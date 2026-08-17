#pragma once

#include <array>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"


#include "main.h"
#include "tools.h"
#include "buffer.h"
#include "message.h"
#include "mnemonics.h"

namespace esphome {
namespace api {
  class CustomAPIDevice;
}
}


namespace esphome {
  namespace api {class CustomAPIDevice; } // forward declaration
namespace hlink2 {


/// Message parameters
struct MessageParameters {
  std::optional<uint32_t> update_interval{std::nullopt};
  std::optional<Message::QoS> qos{};
  std::optional<bool> buzzer{};
  std::optional<bool> ephemeral{};
};


class Core: public uart::UARTDevice, public Component {
  public:
    using PersistentVector = RingVector<Message, MESSAGE_PERSISTENT_VECTOR_SIZE>;
    using EphemeralVector = RingVector<Message, MESSAGE_EPHEMERAL_VECTOR_SIZE>;

    enum class Task: uint8_t {
      EXCHANGE = 0,
      PROCESS = 1,
      size = 2,
      None = 0xFF
    };

    Core();

    /// override Component setup
    void setup() override;

    /// override Component loop
    void loop() override;

    /// override Component dump_config
    void dump_config() override;

    /// set Core task
    inline void set_task(const Task &task) { this->current_task_ = task;}

    /// return next Core task
    inline Task next_task() {
      return static_cast<Task>((static_cast<uint8_t>(this->current_task_) + 1 ) % static_cast<uint8_t>(Task::size));
    }
    
    /// return current Core task
    inline Task task() { return this->current_task_; }

    /// force update of all status messages, disregarding their update interval
    void force_update_messages();

    /// Configure and run the two-stage RAC startup used by the stock Wi-Fi module.
    void set_rac_factory_credentials(std::string ssid, std::string key) {
      this->rac_factory_ssid_ = std::move(ssid);
      this->rac_factory_key_ = std::move(key);
    }
    void set_rac_premium_polling_enabled(bool enabled) {
      this->rac_premium_polling_enabled_ = enabled;
    }
    template<typename FUNC>
    void add_rac_premium_snapshot_callback(FUNC&& callback) {
      this->rac_premium_snapshot_callbacks_.add_callback(std::forward<FUNC>(callback));
    }
    void start_rac_handshake();
    void set_rac_wifi_ready(bool ready);
    std::string rac_handshake_diagnostic() const;
    std::string rac_premium_poll_diagnostic() const;

    /// register a message (either persistent or ephemera)
    template<typename TYPE, Mnemonic::Mode, Mnemonic::Dest>
    Message* register_message(MessageParameters = {});

    /// register a persistent message (helper method)
    template<Mnemonic::Mode MODE, Mnemonic::Dest DEST>
    inline Message* register_persistent_message(MessageParameters params = {}) {
      return register_message<PersistentVector, MODE, DEST>(params); 
    }

    /// register an ephemeral message (helper method)
    template<Mnemonic::Mode MODE, Mnemonic::Dest DEST>
    inline Message* register_ephemeral_message(MessageParameters params = {}) {
      return register_message<EphemeralVector, MODE, DEST>(params);
    }

    /// register a persistent status mnemonic, registering a message if necessary (helper function)
    Message* register_status_mnemonic(Mnemonic&, MessageParameters = {}, bool promote = true);

    /// register an ephemeral custom message with a list of "mnemonics:values"
    template<Mnemonic::Mode MODE>
    Message* register_custom_message(Mnemonic::Dest, std::vector<std::string>, MessageParameters = {});

    /// api action callback to register an ephemeral custom message 
    void action_custom_message(std::string flag, std::vector<std::string> items, int32_t qos = 1);

    /// schedule a message
    void schedule_message(Message*);

    /// return buzzer state for command messages
    inline const bool buzzer() { return this->buzzer_; }
    inline void buzzer(const bool state) { this->buzzer_ = state; }

  protected:
    bool buzzer_{false};
    Task current_task_{Task::EXCHANGE};
    IOBuffer buffer_rx_{};
    api::CustomAPIDevice* api_device_{nullptr};
    PersistentVector persistent_messages_{};
    EphemeralVector ephemeral_messages_{};
    OrderedVector<Message*, PersistentVector::capacity() + EphemeralVector::capacity()> messages_;
    RingVector<Message*, MESSAGE_RECEIVED_VECTOR_SIZE> received_messages;
    Message* current_message_{nullptr};

    enum class RacHandshakeStage : uint8_t {
      IDLE,
      REGISTRATION,
      COMMUNICATION_INIT,
      NORMAL,
    };
    enum class RacAttemptOutcome : uint8_t {
      NONE,
      PENDING,
      ACK,
      NACK,
      TIMEOUT,
      QUEUE_ERROR,
      PARSE_ERROR,
    };
    std::string rac_factory_ssid_{};
    std::string rac_factory_key_{};
    RacHandshakeStage rac_handshake_stage_{RacHandshakeStage::IDLE};
    bool rac_wifi_ready_{false};
    bool rac_premium_polling_enabled_{false};
    bool rac_premium_polling_prepared_{false};
    Message* rac_expected_message_{nullptr};
    Message* rac_wifi_status_message_{nullptr};
    Message* rac_premium_poll_message_{nullptr};
    std::array<Message*, 4> rac_premium_poll_messages_{{nullptr, nullptr, nullptr, nullptr}};
    uint32_t rac_operation_token_{0};
    uint32_t rac_wifi_status_token_{0};
    uint32_t rac_premium_poll_token_{0};
    int8_t rac_registration_response_{-2};
    int8_t rac_communication_init_response_{-2};
    int8_t rac_wifi_status_response_{-2};
    int8_t rac_premium_poll_response_{-2};
    uint16_t rac_registration_attempts_{0};
    uint16_t rac_communication_init_attempts_{0};
    uint16_t rac_wifi_status_attempts_{0};
    uint8_t rac_wifi_status_retry_count_{0};
    uint8_t rac_premium_poll_frame_{0};
    bool rac_premium_idu1_usable_{false};
    uint32_t rac_premium_poll_frames_ok_{0};
    uint32_t rac_premium_poll_frames_failed_{0};
    uint32_t rac_premium_poll_cycles_{0};
    RacAttemptOutcome rac_registration_outcome_{RacAttemptOutcome::NONE};
    RacAttemptOutcome rac_communication_init_outcome_{RacAttemptOutcome::NONE};
    RacAttemptOutcome rac_wifi_status_outcome_{RacAttemptOutcome::NONE};
    RacAttemptOutcome rac_premium_poll_outcome_{RacAttemptOutcome::NONE};
    CallbacksHandler rac_premium_snapshot_callbacks_{};

    Message* send_rac_wifi_status_(uint8_t status);
    void schedule_rac_registration_();
    void schedule_rac_communication_init_();
    void schedule_rac_wifi_ready_();
    bool prepare_rac_premium_poll_();
    void schedule_rac_premium_poll_();
    void arm_rac_premium_poll_(uint32_t delay_ms);
    void advance_rac_premium_poll_();
    void arm_rac_handshake_retry_(uint32_t delay_ms);
    void arm_rac_wifi_status_retry_();
    void handle_rac_message_expiration_(Message* message);
    const char* rac_handshake_stage_name_() const;
    const char* rac_premium_poll_frame_name_() const;
    static const char* rac_attempt_outcome_name_(RacAttemptOutcome outcome);
    void set_rac_current_outcome_(RacAttemptOutcome outcome);
    bool rac_bus_locked_() const;
    Message* rac_locked_message_() const;

    void clear_current_message();
    bool task_schedule();
    void task_format();
    void task_transmit();
    void task_receive();
    void task_parse();
    void task_process();
};


} // hlink2
} //esphome
