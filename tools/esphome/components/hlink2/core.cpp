
#include "esphome/core/log.h"

#include "tools.h"
#include "message.h"
#include "mnemonics.h"
#include <algorithm>
#include <cstddef>
#include <cstdio>
#include <cstdint>
#include <initializer_list>
#include <string>
#include <string_view>
#include <vector>
#include "core.h"
#include "esphome/components/api/custom_api_device.h"

#if defined(USE_LIBRETINY) && defined(HLINK2_UART_RX_IRQ_GUARD)
#include "hlink2_rx_fix.h"
#endif


namespace esphome {
namespace hlink2 {
static const char *const TAG = "hlink2:core";


Core::Core() {
  this->buffer_rx_.set_state(IOBuffer::State::EMPTY);
}


/* ------------------------- SETUP ------------------------- */
void Core::setup() {
  this->set_task(Core::Task::EXCHANGE);
  api_device_ = new api::CustomAPIDevice();
  this->api_device_->register_service(
    &Core::action_custom_message, "send_message",
    std::array<std::string, 3>{{"flag", "items", "qos"}}
  );
}

void Core::dump_config() {
  ESP_LOGCONFIG(TAG, "hlink2 Core");
  ESP_LOGCONFIG(TAG, "Ephemeral Messages: %zu/%zu", this->ephemeral_messages_.size(), this->ephemeral_messages_.capacity());
  ESP_LOGCONFIG(TAG, "Persistent Messages: %zu/%zu", this->persistent_messages_.size(), this->persistent_messages_.capacity());

  for (size_t i=0; i < this->persistent_messages_.size(); i++) {
    ESP_LOGCONFIG(TAG, " %s", this->persistent_messages_[i].config().c_str());
  }
}


template<typename TYPE, Mnemonic::Mode MODE, Mnemonic::Dest DEST>
Message* Core::register_message(MessageParameters params){
  constexpr const Message::Flag& flag = *Message::Flag::flag(MODE, DEST);

  TYPE* vector{nullptr};
  if constexpr (std::is_same_v<TYPE, Core::EphemeralVector>) {
    vector = &this->ephemeral_messages_;
    params.ephemeral = true;
  } else if constexpr (std::is_same_v<TYPE, Core::PersistentVector>) {
    vector = &this->persistent_messages_;
    params.ephemeral = false;
  } else {
    static_assert(std::is_same_v<TYPE, Core::EphemeralVector> || std::is_same_v<TYPE, Core::PersistentVector>, "register_message: bad TYPE");
  }

  if (vector->full()) {
    ESP_LOGE(TAG, "register_message: vector full");
    return nullptr;
  }

  if constexpr (MODE == Mnemonic::Mode::STS) {
    params.update_interval = params.update_interval.value_or(MESSAGE_UPDATE_INTERVAL);
    params.qos = params.qos.value_or(static_cast<Message::QoS>(CONF_MESSAGE_STS_QOS));
  } else if constexpr (MODE == Mnemonic::Mode::CMD) {
    params.update_interval = 0;
    params.qos = params.qos.value_or(static_cast<Message::QoS>(CONF_MESSAGE_CMD_QOS));
    params.buzzer = params.buzzer.value_or(MESSAGE_BUZZER);
  } else {
    static_assert(MODE == Mnemonic::Mode::STS || MODE == Mnemonic::Mode::CMD, "register_message: bad MODE");
  }

  if (vector->emplace_back(flag, *params.qos, *params.update_interval, *params.ephemeral)) {
    Message& msg = vector->back();
    this->messages_.add(&msg);
    ESP_LOGD(TAG, "New %s message @%p", flag.raw, &msg);
    msg.initialize();
    if constexpr (MODE == Mnemonic::Mode::STS) {
      msg.interval().restart();
    }
    if constexpr (MODE == Mnemonic::Mode::CMD) {
      if (*params.buzzer) msg.add(Mnemonic::IDU_Buzz);
    }
    return &msg;
  }
  ESP_LOGE(TAG, "register_message: failed to add message (size=%zu)", vector->size());
  return nullptr;
}

// explicit declarations of register_message
template Message *Core::register_message<Core::PersistentVector, Mnemonic::Mode::CMD, Mnemonic::Dest::IDU>(MessageParameters);
template Message *Core::register_message<Core::PersistentVector, Mnemonic::Mode::CMD, Mnemonic::Dest::ODU>(MessageParameters);
template Message *Core::register_message<Core::PersistentVector, Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(MessageParameters);
template Message *Core::register_message<Core::PersistentVector, Mnemonic::Mode::STS, Mnemonic::Dest::ODU>(MessageParameters);
template Message *Core::register_message<Core::EphemeralVector, Mnemonic::Mode::CMD, Mnemonic::Dest::IDU>(MessageParameters);
template Message *Core::register_message<Core::EphemeralVector, Mnemonic::Mode::CMD, Mnemonic::Dest::ODU>(MessageParameters);
template Message *Core::register_message<Core::EphemeralVector, Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(MessageParameters);
template Message *Core::register_message<Core::EphemeralVector, Mnemonic::Mode::STS, Mnemonic::Dest::ODU>(MessageParameters);


Message* Core::register_status_mnemonic(Mnemonic& m, MessageParameters params, bool promote) {
  if (!m.match_mode(Mnemonic::Mode::STS)) {
    ESP_LOGE(TAG, "register_status_mnemonic: %s: invalid mode (%lu)", m.name, m.mode());
    return nullptr;
  }
  params.update_interval = params.update_interval.value_or(MESSAGE_UPDATE_INTERVAL);
  params.qos = params.qos.value_or(Message::QoS::QOS_LOW);

  if (promote) {
    for (size_t i=0; i< this->persistent_messages_.size(); i++) {
      if (
        this->persistent_messages_[i].flag->match_mode(Mnemonic::Mode::STS)
        && this->persistent_messages_[i].flag->match_dest(m.dest)
        && this->persistent_messages_[i].interval().delay() <= *params.update_interval
        && this->persistent_messages_[i].qos >= *params.qos
      ){
        // promote if already in message
        if (this->persistent_messages_[i].has(m)) {
          return &this->persistent_messages_[i];
        };
        if (
          this->persistent_messages_[i].interval().delay() == *params.update_interval
          && this->persistent_messages_[i].add(m)
        ) {
          return &this->persistent_messages_[i];
        }
      }
    }
  }
  Message* msg;
  switch (m.dest) {
    case Mnemonic::Dest::IDU:
      msg = this->register_message<Core::PersistentVector, Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(params);
      break;
    case Mnemonic::Dest::ODU:
      msg = this->register_message<Core::PersistentVector, Mnemonic::Mode::STS, Mnemonic::Dest::ODU>(params);
      break;
    default: return nullptr;
  }
  if(msg) {
    if (msg->add(m)) {
      return msg;
    } else {
      ESP_LOGE(TAG, "register_status_mnemonic: failed to add mnemonic %s", m.name);
      this->messages_.pop_back(msg);
    }
  }
  return nullptr;
}

template<Mnemonic::Mode MODE>
Message* Core::register_custom_message(Mnemonic::Dest dest, std::vector<std::string> items, MessageParameters params) {
  Message* msg{nullptr};

  switch (dest) {
    case Mnemonic::Dest::IDU:
      msg = this->register_ephemeral_message<MODE, Mnemonic::Dest::IDU>(params);
      break;
    case Mnemonic::Dest::ODU:
      msg = this->register_ephemeral_message<MODE, Mnemonic::Dest::ODU>(params);
      break;
    default:
      ESP_LOGE(TAG, "register_custom_message: invalid dest %u", dest);
      return nullptr;
  }
  if (msg) {
    Mnemonic* mn;
    std::string_view name;
    std::string_view value;
    for (std::string item: items) {
      if constexpr (MODE == Mnemonic::Mode::CMD) {
        const char* split = item.c_str();
        while (*split && *split != ':') split++;
        if (*split == '\0') {
          ESP_LOGW(TAG, "register_custom_message: missing ':' (%s)", item);
          continue;
        }
        name = std::string_view(item.c_str(), split - item.c_str());
        value = std::string_view(split + 1);
      } else {
        name = std::string_view(item);
      }

      mn = Mnemonic::from_hash(name, dest);
      if (mn == &Mnemonic::None) {
        ESP_LOGW(TAG, "register_custom_message: unknow mnemonic %s_%.*s", Mnemonic::DestToString(dest), name.size(), name.data());
        continue;
      }
      if (auto request = msg->add(*mn)) {
        if constexpr (MODE == Mnemonic::Mode::CMD) {
          if (request->set_request(value, true) ) {
          } else {
            ESP_LOGE(TAG, "register_custom_message: failed to add request (%.*s)", value.size(), value.data());
          }
        }
      } else {
        ESP_LOGW(TAG, "register_custom_message: failed to add mnemonic %s_%.*s",  Mnemonic::DestToString(dest), name.size(), name.data());
      }
    }
    if (msg->empty()) {
      ESP_LOGW(TAG, "register_custom_message: empty message");
      msg->set_state(Message::State::INVALID); // garbage collection
      return nullptr;
    }
    this->schedule_message(msg);
    ESP_LOGI(TAG, "register_custom_message: registered %s", msg->config().c_str());
    return msg;
  }
  ESP_LOGE(TAG, "register_custom_message: registration failed");
  return nullptr;
}


void Core::action_custom_message(std::string flag, std::vector<std::string> items, int32_t qos) {
  const Message::Flag* f = Message::Flag::from_raw(flag);
  Message* msg;
  switch (f->mode) {
    case Mnemonic::Mode::STS:
      msg = register_custom_message<Mnemonic::Mode::STS>(f->dest, items, MessageParameters{.qos = static_cast<Message::QoS>(qos), .ephemeral=true});
      break;
    case Mnemonic::Mode::CMD:
      msg = register_custom_message<Mnemonic::Mode::CMD>(f->dest, items, MessageParameters{.qos = static_cast<Message::QoS>(qos), .buzzer=true, .ephemeral=true});
      break;
    default:
      ESP_LOGE(TAG, "action_custom_message: invalid mode (flag %s -> %s)", flag.c_str(), f->raw);
      return;
  }      
}

void Core::schedule_message(Message* msg) {
  msg->reinitialize();
  msg->schedule();
}

void Core::force_update_messages() {
  for (size_t index = 0; index < this->persistent_messages_.size(); ++index) {
    if (this->persistent_messages_[index].interval().delay() && this->persistent_messages_[index].state() == Message::State::INITIALIZED) {
      this->persistent_messages_[index].interval().force_expiration();
    }
  }
}

Message* Core::send_rac_wifi_status_(uint8_t status) {
  std::vector<std::string> items{"WSt:" + std::to_string(status)};
  Message *message = this->register_custom_message<Mnemonic::Mode::CMD>(
    Mnemonic::Dest::IDU,
    std::move(items),
    MessageParameters{
      .qos = Message::QoS::QOS_HIGH,
      .buzzer = false,
      .ephemeral = true,
    }
  );
  if (message == nullptr) {
    ESP_LOGW(TAG, "RAC handshake: failed to queue WSt=%u", status);
  } else {
    ESP_LOGI(TAG, "RAC handshake: queued WSt=%u", status);
  }
  return message;
}

const char* Core::rac_handshake_stage_name_() const {
  switch (this->rac_handshake_stage_) {
    case RacHandshakeStage::IDLE:
      return "IDLE";
    case RacHandshakeStage::REGISTRATION:
      return "REGISTRATION";
    case RacHandshakeStage::COMMUNICATION_INIT:
      return "COMMUNICATION_INIT";
    case RacHandshakeStage::NORMAL:
      return "NORMAL";
  }
  return "UNKNOWN";
}

const char* Core::rac_premium_poll_frame_name_() const {
  switch (this->rac_premium_poll_frame_) {
    case 0:
      return "IDU1";
    case 1:
      return "IDU2";
    case 2:
      return "IDU3";
    case 3:
      return "ODU";
  }
  return "?";
}

const char* Core::rac_attempt_outcome_name_(RacAttemptOutcome outcome) {
  switch (outcome) {
    case RacAttemptOutcome::NONE:
      return "NONE";
    case RacAttemptOutcome::PENDING:
      return "WAIT";
    case RacAttemptOutcome::ACK:
      return "ACK";
    case RacAttemptOutcome::NACK:
      return "NACK";
    case RacAttemptOutcome::TIMEOUT:
      return "TIMEOUT";
    case RacAttemptOutcome::QUEUE_ERROR:
      return "QUEUE";
    case RacAttemptOutcome::PARSE_ERROR:
      return "PARSE";
  }
  return "?";
}

void Core::set_rac_current_outcome_(RacAttemptOutcome outcome) {
  switch (this->rac_handshake_stage_) {
    case RacHandshakeStage::REGISTRATION:
      this->rac_registration_outcome_ = outcome;
      return;
    case RacHandshakeStage::COMMUNICATION_INIT:
      this->rac_communication_init_outcome_ = outcome;
      return;
    case RacHandshakeStage::IDLE:
    case RacHandshakeStage::NORMAL:
      return;
  }
}

bool Core::rac_bus_locked_() const {
  if (this->rac_handshake_stage_ == RacHandshakeStage::REGISTRATION) {
    return this->rac_registration_outcome_ != RacAttemptOutcome::QUEUE_ERROR;
  }
  if (this->rac_handshake_stage_ == RacHandshakeStage::COMMUNICATION_INIT) {
    return this->rac_communication_init_outcome_ != RacAttemptOutcome::QUEUE_ERROR;
  }
  // Keep the three contiguous IDU frames intact. The lock is released during
  // the stock one-second IDU->ODU and ODU->IDU gaps, so climate commands are
  // never held behind a continuously running status poller.
  return this->rac_premium_poll_message_ != nullptr;
}

Message* Core::rac_locked_message_() const {
  if (this->rac_expected_message_ != nullptr) {
    return this->rac_expected_message_;
  }
  return this->rac_premium_poll_message_;
}

std::string Core::rac_handshake_diagnostic() const {
  char buffer[192];
  std::snprintf(
    buffer,
    sizeof(buffer),
    "%s reg=%s/r%d/n%u init=%s/r%d/n%u wst=%s/r%d/n%u",
    this->rac_handshake_stage_name_(),
    this->rac_attempt_outcome_name_(this->rac_registration_outcome_),
    static_cast<int>(this->rac_registration_response_),
    static_cast<unsigned>(this->rac_registration_attempts_),
    this->rac_attempt_outcome_name_(this->rac_communication_init_outcome_),
    static_cast<int>(this->rac_communication_init_response_),
    static_cast<unsigned>(this->rac_communication_init_attempts_),
    this->rac_attempt_outcome_name_(this->rac_wifi_status_outcome_),
    static_cast<int>(this->rac_wifi_status_response_),
    static_cast<unsigned>(this->rac_wifi_status_attempts_)
  );
  return std::string(buffer);
}

std::string Core::rac_premium_poll_diagnostic() const {
  char buffer[160];
  std::snprintf(
    buffer,
    sizeof(buffer),
    "%s %s/r%d cycles=%lu ok=%lu fail=%lu",
    this->rac_premium_poll_frame_name_(),
    this->rac_attempt_outcome_name_(this->rac_premium_poll_outcome_),
    static_cast<int>(this->rac_premium_poll_response_),
    static_cast<unsigned long>(this->rac_premium_poll_cycles_),
    static_cast<unsigned long>(this->rac_premium_poll_frames_ok_),
    static_cast<unsigned long>(this->rac_premium_poll_frames_failed_)
  );
  return std::string(buffer);
}

void Core::arm_rac_handshake_retry_(uint32_t delay_ms) {
  this->set_timeout("rac_handshake_retry", delay_ms, [this]() {
    switch (this->rac_handshake_stage_) {
      case RacHandshakeStage::REGISTRATION:
        ESP_LOGW(TAG, "RAC handshake: registration timed out; retrying registration");
        this->rac_expected_message_ = nullptr;
        this->schedule_rac_registration_();
        return;
      case RacHandshakeStage::COMMUNICATION_INIT:
        ESP_LOGW(TAG, "RAC handshake: communication-init timed out; retrying communication-init");
        this->rac_expected_message_ = nullptr;
        this->schedule_rac_communication_init_();
        return;
      case RacHandshakeStage::IDLE:
      case RacHandshakeStage::NORMAL:
        return;
    }
  });
}

void Core::arm_rac_wifi_status_retry_() {
  if (this->rac_wifi_status_retry_count_ >= 3) {
    ESP_LOGW(TAG, "RAC Wi-Fi status: WSt=1 gave no usable response after 3 attempts");
    return;
  }
  this->set_timeout("rac_wifi_status_retry", 7000, [this]() {
    if (
      this->rac_handshake_stage_ == RacHandshakeStage::NORMAL
      && this->rac_wifi_ready_
      && this->rac_wifi_status_message_ == nullptr
    ) {
      this->schedule_rac_wifi_ready_();
    }
  });
}

void Core::handle_rac_message_expiration_(Message* message) {
  if (message == this->rac_expected_message_) {
    this->rac_expected_message_ = nullptr;
    switch (this->rac_handshake_stage_) {
      case RacHandshakeStage::REGISTRATION:
        if (this->rac_registration_outcome_ != RacAttemptOutcome::PARSE_ERROR) {
          this->rac_registration_outcome_ = RacAttemptOutcome::TIMEOUT;
        }
        break;
      case RacHandshakeStage::COMMUNICATION_INIT:
        if (this->rac_communication_init_outcome_ != RacAttemptOutcome::PARSE_ERROR) {
          this->rac_communication_init_outcome_ = RacAttemptOutcome::TIMEOUT;
        }
        break;
      case RacHandshakeStage::IDLE:
      case RacHandshakeStage::NORMAL:
        break;
    }
    // The per-message timeout starts only when the message reaches the bus.
    // Schedule the outer stage retry from that actual expiration, never from
    // initial queue time, so a still-live request cannot be replaced.
    this->arm_rac_handshake_retry_(3000);
  }
  if (message == this->rac_wifi_status_message_) {
    this->rac_wifi_status_message_ = nullptr;
    if (this->rac_wifi_status_outcome_ != RacAttemptOutcome::PARSE_ERROR) {
      this->rac_wifi_status_outcome_ = RacAttemptOutcome::TIMEOUT;
    }
    if (this->rac_wifi_ready_) {
      this->arm_rac_wifi_status_retry_();
    }
  }
  if (message == this->rac_premium_poll_message_) {
    this->rac_premium_poll_message_ = nullptr;
    if (this->rac_premium_poll_outcome_ != RacAttemptOutcome::PARSE_ERROR) {
      this->rac_premium_poll_outcome_ = RacAttemptOutcome::TIMEOUT;
    }
    ++this->rac_premium_poll_frames_failed_;
    ESP_LOGW(
      TAG,
      "RAC Premium polling: %s expired",
      this->rac_premium_poll_frame_name_()
    );
    this->advance_rac_premium_poll_();
  }
}

void Core::schedule_rac_registration_() {
  this->rac_handshake_stage_ = RacHandshakeStage::REGISTRATION;
  const uint32_t operation_token = ++this->rac_operation_token_;
  std::vector<std::string> items{
    "WSt:1",
    "TYPE:0",
    "SSID:\"" + this->rac_factory_ssid_ + "\"",
    "Pwd:\"" + this->rac_factory_key_ + "\"",
  };
  Message *message = this->register_custom_message<Mnemonic::Mode::CMD>(
    Mnemonic::Dest::IDU,
    std::move(items),
    MessageParameters{
      .qos = Message::QoS::QOS_HIGH,
      .buzzer = false,
      .ephemeral = true,
    }
  );
  ++this->rac_registration_attempts_;
  this->rac_registration_response_ = -1;
  this->rac_expected_message_ = message;
  if (message == nullptr) {
    this->rac_registration_outcome_ = RacAttemptOutcome::QUEUE_ERROR;
    ESP_LOGE(TAG, "RAC handshake: failed to queue registration");
    this->arm_rac_handshake_retry_(7000);
    return;
  }
  this->rac_registration_outcome_ = RacAttemptOutcome::PENDING;

  // Stock checks only framing/checksum at this stage and advances even when
  // the response has no payload or carries a non-zero Res code.
  message->set_response_policy(Message::ResponsePolicy::ANY_CHECKSUMMED);
  message->add_callback([this, message, operation_token]() {
    if (
      this->rac_handshake_stage_ != RacHandshakeStage::REGISTRATION
      || this->rac_expected_message_ != message
      || this->rac_operation_token_ != operation_token
    ) {
      return;
    }
    this->rac_registration_response_ = message->response
      ? static_cast<int8_t>(*message->response)
      : -1;
    this->rac_registration_outcome_ = RacAttemptOutcome::ACK;
    ESP_LOGI(
      TAG,
      "RAC handshake: registration got checksum-valid response Res=%d",
      static_cast<int>(this->rac_registration_response_)
    );
    this->rac_expected_message_ = nullptr;
    this->schedule_rac_communication_init_();
  });
  ESP_LOGI(
    TAG,
    "RAC handshake: registration queued (attempt %u)",
    static_cast<unsigned>(this->rac_registration_attempts_)
  );
}

void Core::schedule_rac_communication_init_() {
  this->rac_handshake_stage_ = RacHandshakeStage::COMMUNICATION_INIT;
  const uint32_t operation_token = ++this->rac_operation_token_;
  std::vector<std::string> items{"Modl", "TPID", "PwrZ", "SwrZ", "ItW", "Fota"};
  Message *message = this->register_custom_message<Mnemonic::Mode::STS>(
    Mnemonic::Dest::IDU,
    std::move(items),
    MessageParameters{
      .qos = Message::QoS::QOS_HIGH,
      .ephemeral = true,
    }
  );
  ++this->rac_communication_init_attempts_;
  this->rac_communication_init_response_ = -1;
  this->rac_expected_message_ = message;
  if (message == nullptr) {
    this->rac_communication_init_outcome_ = RacAttemptOutcome::QUEUE_ERROR;
    ESP_LOGE(TAG, "RAC handshake: failed to queue communication-init");
    this->arm_rac_handshake_retry_(7000);
    return;
  }
  this->rac_communication_init_outcome_ = RacAttemptOutcome::PENDING;

  // The stock Premium path proceeds after a non-empty receive operation. Requiring
  // Res=0 here is stricter than stock and can strand the module in pairing mode.
  message->set_response_policy(Message::ResponsePolicy::ANY_CHECKSUMMED);
  message->add_callback([this, message, operation_token]() {
    if (
      this->rac_handshake_stage_ != RacHandshakeStage::COMMUNICATION_INIT
      || this->rac_expected_message_ != message
      || this->rac_operation_token_ != operation_token
    ) {
      return;
    }
    this->rac_communication_init_response_ = message->response
      ? static_cast<int8_t>(*message->response)
      : -1;
    this->rac_communication_init_outcome_ = RacAttemptOutcome::ACK;
    ESP_LOGI(
      TAG,
      "RAC handshake: communication-init got checksum-valid response Res=%d",
      static_cast<int>(this->rac_communication_init_response_)
    );
    this->rac_expected_message_ = nullptr;
    this->rac_handshake_stage_ = RacHandshakeStage::NORMAL;
    this->cancel_timeout("rac_handshake_retry");
    ESP_LOGI(TAG, "RAC handshake: communication initialization complete; RAC is NORMAL");
    if (this->rac_wifi_ready_) {
      this->rac_wifi_status_retry_count_ = 0;
      this->schedule_rac_wifi_ready_();
    }
    if (this->rac_premium_polling_enabled_) {
      this->rac_premium_poll_frame_ = 0;
      this->arm_rac_premium_poll_(1000);
    }
  });
  ESP_LOGI(
    TAG,
    "RAC handshake: communication-init queued (attempt %u)",
    static_cast<unsigned>(this->rac_communication_init_attempts_)
  );
}

void Core::schedule_rac_wifi_ready_() {
  if (
    this->rac_handshake_stage_ != RacHandshakeStage::NORMAL
    || !this->rac_wifi_ready_
    || this->rac_wifi_status_message_ != nullptr
  ) {
    return;
  }
  const uint32_t operation_token = ++this->rac_wifi_status_token_;
  Message *message = this->send_rac_wifi_status_(1);
  ++this->rac_wifi_status_attempts_;
  ++this->rac_wifi_status_retry_count_;
  this->rac_wifi_status_response_ = -1;
  this->rac_wifi_status_message_ = message;
  if (message == nullptr) {
    this->rac_wifi_status_outcome_ = RacAttemptOutcome::QUEUE_ERROR;
    this->arm_rac_wifi_status_retry_();
    return;
  }
  this->rac_wifi_status_outcome_ = RacAttemptOutcome::PENDING;

  // This is a separate local approximation of stock "Cloud Connection Done",
  // not a gate for RAC NORMAL. Observe its checksum-valid response independently.
  message->set_response_policy(Message::ResponsePolicy::ANY_CHECKSUMMED);
  message->add_callback([this, message, operation_token]() {
    if (
      this->rac_wifi_status_message_ != message
      || this->rac_wifi_status_token_ != operation_token
    ) {
      return;
    }
    this->rac_wifi_status_response_ = message->response
      ? static_cast<int8_t>(*message->response)
      : -1;
    this->rac_wifi_status_message_ = nullptr;
    if (message->response && *message->response == Message::Response::VALID) {
      this->rac_wifi_status_outcome_ = RacAttemptOutcome::ACK;
      this->cancel_timeout("rac_wifi_status_retry");
      ESP_LOGI(TAG, "RAC Wi-Fi status: WSt=1 accepted");
      return;
    }
    this->rac_wifi_status_outcome_ = RacAttemptOutcome::NACK;
    ESP_LOGW(
      TAG,
      "RAC Wi-Fi status: WSt=1 returned Res=%d",
      static_cast<int>(this->rac_wifi_status_response_)
    );
  });
  ESP_LOGI(
    TAG,
    "RAC Wi-Fi status: WSt=1 queued (attempt %u)",
    static_cast<unsigned>(this->rac_wifi_status_attempts_)
  );
}

bool Core::prepare_rac_premium_poll_() {
  if (this->rac_premium_polling_prepared_) {
    return true;
  }

  const MessageParameters parameters{
    .update_interval = 0,
    .qos = Message::QoS::QOS_LOW,
    .ephemeral = false,
  };
  this->rac_premium_poll_messages_[0] =
    this->register_persistent_message<Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(parameters);
  this->rac_premium_poll_messages_[1] =
    this->register_persistent_message<Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(parameters);
  this->rac_premium_poll_messages_[2] =
    this->register_persistent_message<Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(parameters);
  this->rac_premium_poll_messages_[3] =
    this->register_persistent_message<Mnemonic::Mode::STS, Mnemonic::Dest::ODU>(parameters);

  const auto add_frame = [](Message* message, Mnemonic::Dest dest,
                            std::initializer_list<const char*> names) -> bool {
    if (message == nullptr) {
      return false;
    }
    for (const char* name : names) {
      Mnemonic* mnemonic = Mnemonic::from_hash(std::string_view(name), dest);
      if (mnemonic == &Mnemonic::None || message->add(*mnemonic) == nullptr) {
        ESP_LOGE(
          TAG,
          "RAC Premium polling: cannot add %s_%s",
          Mnemonic::DestToString(dest),
          name
        );
        return false;
      }
    }
    return true;
  };

  // Exact enabled portion of the stock 55-entry Premium table. Its first five
  // descriptors belong to communication-init and are disabled for NORMAL.
  const bool frames_ok =
    add_frame(
      this->rac_premium_poll_messages_[0],
      Mnemonic::Dest::IDU,
      {
        "Stat", "ALM", "OnOf", "Mode", "Thmo", "SetT", "SetTR", "Hs", "FanS",
        "FanHD", "FanSw", "FilS", "PwrI", "PwrC", "CapC", "RlMd", "MdDtl",
        "Maint", "Tr",
      }
    )
    && add_frame(
      this->rac_premium_poll_messages_[1],
      Mnemonic::Dest::IDU,
      {
        "Hr", "FltT", "Rair", "HExT", "Comm", "PinR", "Opt1", "Opt2", "Opt3",
        "Opt4", "Opt5", "Opt6", "Opt7", "Opt8", "Func1", "Func2", "Func3",
        "Func4", "Func5",
      }
    )
    && add_frame(
      this->rac_premium_poll_messages_[2],
      Mnemonic::Dest::IDU,
      {
        "Func6", "ItW", "Dmd", "Cinfo", "Info1", "Info2", "Info3", "Info4",
        "Info5",
      }
    )
    && add_frame(
      this->rac_premium_poll_messages_[3],
      Mnemonic::Dest::ODU,
      {"HExT", "H1", "Ta"}
    );

  if (!frames_ok) {
    this->rac_premium_poll_outcome_ = RacAttemptOutcome::QUEUE_ERROR;
    ESP_LOGE(TAG, "RAC Premium polling: failed to prepare the stock frame set");
    return false;
  }

  for (uint8_t frame = 0; frame < this->rac_premium_poll_messages_.size(); ++frame) {
    Message* message = this->rac_premium_poll_messages_[frame];
    message->set_response_policy(Message::ResponsePolicy::TRACK_CHECKSUMMED);
    message->add_callback([this, message, frame]() {
      if (
        this->rac_handshake_stage_ != RacHandshakeStage::NORMAL
        || this->rac_premium_poll_message_ != message
        || this->rac_premium_poll_frame_ != frame
      ) {
        return;
      }

      this->rac_premium_poll_response_ = message->response
        ? static_cast<int8_t>(*message->response)
        : -1;
      const bool usable =
        message->response
        && (
          *message->response == Message::Response::VALID
          || *message->response == Message::Response::PARTIAL
        );
      if (frame == 0) {
        this->rac_premium_idu1_usable_ = usable;
      }
      if (usable) {
        this->rac_premium_poll_outcome_ = RacAttemptOutcome::ACK;
        ++this->rac_premium_poll_frames_ok_;
        if (frame == 1 && this->rac_premium_idu1_usable_) {
          // IDU2 completes the climate snapshot: IDU1 carries the operating
          // state and IDU2 carries humidity plus Opt1..Opt4 (preset).
          this->rac_premium_snapshot_callbacks_.run_callbacks();
        }
      } else {
        this->rac_premium_poll_outcome_ = RacAttemptOutcome::NACK;
        ++this->rac_premium_poll_frames_failed_;
        ESP_LOGW(
          TAG,
          "RAC Premium polling: %s returned Res=%d",
          this->rac_premium_poll_frame_name_(),
          static_cast<int>(this->rac_premium_poll_response_)
        );
      }

      this->rac_premium_poll_message_ = nullptr;
      this->advance_rac_premium_poll_();
    });
  }

  this->rac_premium_polling_prepared_ = true;
  ESP_LOGI(TAG, "RAC Premium polling: prepared stock 19/19/9 IDU + 3 ODU frames");
  return true;
}

void Core::schedule_rac_premium_poll_() {
  if (
    !this->rac_premium_polling_enabled_
    || this->rac_handshake_stage_ != RacHandshakeStage::NORMAL
    || this->rac_premium_poll_message_ != nullptr
    || !this->prepare_rac_premium_poll_()
  ) {
    return;
  }

  Message* message = this->rac_premium_poll_messages_[this->rac_premium_poll_frame_];
  if (message == nullptr) {
    this->rac_premium_poll_outcome_ = RacAttemptOutcome::QUEUE_ERROR;
    ++this->rac_premium_poll_frames_failed_;
    ESP_LOGE(
      TAG,
      "RAC Premium polling: missing frame %s",
      this->rac_premium_poll_frame_name_()
    );
    this->advance_rac_premium_poll_();
    return;
  }

  ++this->rac_premium_poll_token_;
  if (this->rac_premium_poll_frame_ == 0) {
    this->rac_premium_idu1_usable_ = false;
  }
  this->rac_premium_poll_response_ = -1;
  this->rac_premium_poll_outcome_ = RacAttemptOutcome::PENDING;
  this->rac_premium_poll_message_ = message;
  this->schedule_message(message);
  ESP_LOGD(
    TAG,
    "RAC Premium polling: queued %s",
    this->rac_premium_poll_frame_name_()
  );
}

void Core::arm_rac_premium_poll_(uint32_t delay_ms) {
  this->cancel_timeout("rac_premium_poll");
  if (delay_ms == 0) {
    this->schedule_rac_premium_poll_();
    return;
  }
  this->set_timeout("rac_premium_poll", delay_ms, [this]() {
    this->schedule_rac_premium_poll_();
  });
}

void Core::advance_rac_premium_poll_() {
  const uint8_t completed_frame = this->rac_premium_poll_frame_;
  if (completed_frame == 3) {
    ++this->rac_premium_poll_cycles_;
    if (this->rac_premium_poll_cycles_ == 1) {
      ESP_LOGI(TAG, "RAC Premium polling: first complete stock cycle finished");
    }
  }
  this->rac_premium_poll_frame_ =
    static_cast<uint8_t>((this->rac_premium_poll_frame_ + 1) % this->rac_premium_poll_messages_.size());

  // Stock emits the first two full 19-field IDU batches back-to-back. It waits
  // one second after the short final IDU batch and another second after ODU.
  this->arm_rac_premium_poll_(completed_frame >= 2 ? 1000 : 0);
}

void Core::start_rac_handshake() {
  if (this->rac_handshake_stage_ != RacHandshakeStage::IDLE) {
    return;
  }
  if (this->rac_factory_ssid_.empty() || this->rac_factory_key_.empty()) {
    ESP_LOGE(TAG, "RAC handshake: factory SSID/key are not configured");
    return;
  }
  // Stock RAC order is registration -> communication-init -> NORMAL. A short
  // WSt=0 before registration is a separate main-task status and leaves the DJ25
  // visibly in AP mode if the response-dependent stages do not complete.
  this->schedule_rac_registration_();
}

void Core::set_rac_wifi_ready(bool ready) {
  if (this->rac_wifi_ready_ == ready) {
    return;
  }
  this->rac_wifi_ready_ = ready;
  if (!ready) {
    this->cancel_timeout("rac_wifi_status_retry");
    if (
      this->rac_wifi_status_message_ != nullptr
      && this->rac_wifi_status_message_ != this->current_message_
      && (
        this->rac_wifi_status_message_->raw_state() == Message::State::SCHEDULED
        || this->rac_wifi_status_message_->raw_state() == Message::State::FORMATTED
      )
    ) {
      this->rac_wifi_status_message_->set_state(Message::State::EXPIRED);
      this->rac_wifi_status_message_ = nullptr;
      ++this->rac_wifi_status_token_;
      this->rac_wifi_status_outcome_ = RacAttemptOutcome::NONE;
      this->rac_wifi_status_response_ = -1;
    }
    return;
  }

  this->rac_wifi_status_retry_count_ = 0;
  if (this->rac_handshake_stage_ == RacHandshakeStage::NORMAL) {
    this->schedule_rac_wifi_ready_();
  }
}

/* ------------------------- STATE MACHINE ------------------------- */

void Core::clear_current_message() {
  if (
    this->current_message_->flag->match_mode(Mnemonic::Mode::CMD)
    && this->current_message_->state() > Message::State::PARSED
  ) {
    this->current_message_->clear_requests();
  }
  this->current_message_ = nullptr;
}

void Core::loop() {
  // This component runs in LibreTiny's high-priority Arduino task. The old loop
  // deliberately stayed here until TASK_TIMEOUT expired, even when there was no
  // work to do. task_receive() had another wait loop, so a single ESPHome pass
  // could monopolise the CPU for 30-60 ms and starve Realtek's Wi-Fi/LwIP tasks.
  // Execute one bounded unit of work and immediately give ESPHome control back:
  // one I/O state step, or parse/publish one complete reply snapshot. There is
  // no timer-budget loop and no waiting for future UART bytes.
  switch (this->current_task_) {
    case Task::EXCHANGE: {
      if (!this->current_message_) {
        // Finish publishing the previous reply before starting a new request.
        if (!this->received_messages.empty()) {
          this->set_task(Task::PROCESS);
          return;
        }
        // Scheduling is itself one state-machine step. Formatting starts on the
        // next ESPHome pass so even the selection path remains bounded.
        if (!this->task_schedule()) {
          this->set_task(Task::PROCESS);
        }
        return;
      }

      const Message::State current_state = this->current_message_->state();
      switch (current_state) {
        case Message::State::SCHEDULED:
          this->task_format();
          return;
        case Message::State::FORMATTED:
          this->task_transmit();
          return;
        case Message::State::SENT:
          this->task_receive();
          return;
        case Message::State::RECEIVED: {
          Message* parsed_message = this->current_message_;
          this->task_parse();
          if (!this->current_message_) {
            this->set_task(Task::PROCESS);
            // Publish one complete reply in the same component call in which
            // it was parsed. This keeps each status snapshot atomic and keeps
            // a new API control from reinitializing a queued CMD object between
            // global ESPHome passes. There is still no wait/spin: work is
            // bounded to the callbacks of this single received message.
            if (
              !this->received_messages.empty()
              && this->received_messages.front() == parsed_message
            ) {
              this->task_process();
              if (this->received_messages.empty()) {
                this->set_task(Task::EXCHANGE);
              }
            }
          }
          return;
        }
        case Message::State::PARSED:
          // task_parse() normally queues the message and clears current_message_.
          // Keep this recovery path for a pre-existing/externally changed state.
          this->clear_current_message();
          this->set_task(Task::PROCESS);
          return;
        case Message::State::EXPIRED:
          ESP_LOGW(TAG, "loop: @%p expired (%s)", this->current_message_, this->current_message_->config().c_str());
          this->handle_rac_message_expiration_(this->current_message_);
          // clear_current_message() deliberately preserves PARSED commands for
          // task_process(), but an expired command must never retain values for
          // the next climate call. Clear it before reinitialize() changes the
          // persistent message state back to INITIALIZED.
          if (this->current_message_->flag->match_mode(Mnemonic::Mode::CMD)) {
            this->current_message_->clear_requests();
          }
          this->current_message_->reinitialize();
          this->clear_current_message();
          this->set_task(Task::PROCESS);
          return;
        default:
          ESP_LOGE(TAG, "loop: @%p: discarded, state %s", this->current_message_, Message::StateName[static_cast<uint8_t>(current_state)]);
          this->clear_current_message();
          this->set_task(Task::PROCESS);
          return;
      }
    }

    case Task::PROCESS:
      if (!this->received_messages.empty()) {
        this->task_process();
      }
      if (this->received_messages.empty()) {
        this->set_task(Task::EXCHANGE);
      }
      return;

    default:
      this->set_task(Task::EXCHANGE);
      return;
  }
}

/* ------------------------- TASKS ------------------------- */

bool Core::task_schedule() {
  ESP_LOGV(TAG, "SCHEDULE: start");

  if ((this->current_message_ = this->messages_.select(
      [this](Message* msg) -> int8_t {
        constexpr int8_t NOT_TERMINAL = 2;
        const auto clean_terminal = [this, msg](Message::State state) -> int8_t {
          if (
            state != Message::State::PROCESSED
            && state != Message::State::EXPIRED
            && state != Message::State::INVALID
          ) {
            return NOT_TERMINAL;
          }
          if (state != Message::State::PROCESSED) {
            this->handle_rac_message_expiration_(msg);
          }
          if (msg->ephemeral()) {
            if (msg == &this->ephemeral_messages_.front()) {
              ESP_LOGD(TAG, "@%p removed from ephemeral messages (%s)", msg, Message::StateName[static_cast<uint8_t>(state)]);
              this->ephemeral_messages_.pop_front();
              return -1;
            }
            return 0;
          }
          msg->reinitialize();
          return NOT_TERMINAL;
        };

        int8_t terminal_result = clean_terminal(msg->raw_state());
        if (terminal_result != NOT_TERMINAL) {
          return terminal_result;
        }

        // The stock RAC startup is a strict request/response sequence. While a
        // stage is active, do not interleave normal climate polling or commands.
        // Message transaction timeouts start only after selection for the bus,
        // so commands queued during startup cannot expire unseen.
        if (
          this->rac_bus_locked_()
          && (this->rac_locked_message_() == nullptr || msg != this->rac_locked_message_())
        ) {
          return 0;
        }

        // In Premium mode the four stock-compatible frames are the sole
        // source of status polling. Suppress the shorter generic STS messages
        // during the intentional one-second gaps, while still allowing CMD.
        if (
          this->rac_premium_polling_enabled_
          && this->rac_premium_polling_prepared_
          && this->rac_handshake_stage_ == RacHandshakeStage::NORMAL
          && msg->flag->match_mode(Mnemonic::Mode::STS)
          && msg != this->rac_premium_poll_message_
        ) {
          return 0;
        }

        const Message::State state = msg->state();
        terminal_result = clean_terminal(state);
        if (terminal_result != NOT_TERMINAL) {
          return terminal_result;
        }

        switch (msg->raw_state()) {
          case Message::State::INITIALIZED:
            if (!msg->interval().expired()) {
              return 0;
            }
            msg->schedule();
            msg->interval().restart();
          case Message::State::SCHEDULED:
            msg->start_transaction_timeout();
            return 1;
          case Message::State::FORMATTED:
            msg->start_transaction_timeout();
            return 1;
          default:
            return 0;
        }
      }
    )
  )) {
    ESP_LOGD(TAG, "SCHEDULE: @%p %s", this->current_message_, this->current_message_->flag->raw);
    return true;
  }

  ESP_LOGV(TAG, "SCHEDULE: no message to schedule");
  return false;
}


void Core::task_format() {
  ESP_LOGV(TAG, "FORMAT: start");
  // A command can be reinitialized by an API control while its Message object
  // is already selected. Ensure that path also gets a transaction timeout.
  this->current_message_->start_transaction_timeout();
  if (this->current_message_->flag->match_mode(Mnemonic::Mode::CMD)) {
    if (auto request = this->current_message_->get_request(Mnemonic::IDU_Buzz)) {
      request->set_request(this->buzzer() ? '1' : '0');
    }
  }
  switch (this->current_message_->format()) { 
    case Message::State::FORMATTED:
      ESP_LOGV(TAG, "FORMAT: @%p: done", this->current_message_);
      return;
    case Message::State::EXPIRED:
      ESP_LOGW(TAG, "FORMAT: expired");
      return;
    default:
      ESP_LOGE(TAG, "FORMAT: failed");
      return;
  }
}


void Core::task_transmit() {
  this->current_message_->start_transaction_timeout();
  IOBuffer* buffer = this->current_message_->request_buffer();
  ESP_LOGV(TAG, "TRANSMIT: start, %zu/%zu bytes", buffer->view_index(), buffer->size());
  
  // empty read buffer (there is no way to know to which message attribute read data)
  // Only before the first chunk: a frame takes several calls to transmit, and the
  // answer to the previous message starts arriving in the middle of that. Draining
  // on every call throws away the head of that answer.
  if (buffer->view_index() == 0) {
    uint8_t buffer_[256];
    const int available_bytes = this->available();
    if (available_bytes > 0) {
      const size_t len = std::min(sizeof(buffer_), static_cast<size_t>(available_bytes));
      if (this->read_array(buffer_, len)) {
        ESP_LOGW(TAG, "TRANSMIT: discarded RX buffer (%zu), %s", len, debug_data(buffer_, len).c_str());
      } else {
        ESP_LOGE(TAG, "TRANSMIT: failed to discard RX buffer");
      }
      // If a future UART buffer is larger than this local chunk, leave the
      // request at offset zero. The next component pass drains the remainder
      // before any request byte is sent.
      return;
    }
  }

  // SerialClass::write() busy-waits for room in the AmebaZ UART FIFO. Send one
  // small chunk per ESPHome pass instead of looping over the entire frame.
  const size_t len = std::min<size_t>(UART_TX_CHUNK_SIZE, buffer->view.size());
  if (len) {
    // ESPHome's UARTDevice::write_array() is a void API on this pinned version;
    // the driver accepts the complete chunk or blocks until it can do so.
    this->write_array(reinterpret_cast<const uint8_t*>(buffer->view.data()), len);
    buffer->view.remove_prefix(len);
  }
  if (!buffer->view.empty()) {
    ESP_LOGV(TAG, "TRANSMIT: partial, %zu/%zu bytes", buffer->view_index(), buffer->size());
    return;
  }

  this->current_message_->set_state(Message::State::SENT);
  this->buffer_rx_.set_state(IOBuffer::State::EMPTY);
  ESP_LOGV(TAG, "TRANSMIT: @%p: done, %zu/%zu bytes", this->current_message_, buffer->view_index(), buffer->size());
  return;
}


void Core::task_receive() {
  ESP_LOGV(TAG, "RECEIVE: start, %zu bytes", this->buffer_rx_.size());

  const auto retry_or_expire = [this]() {
    this->buffer_rx_.set_state(IOBuffer::State::EMPTY);
    if (this->current_message_ == this->rac_expected_message_) {
      this->set_rac_current_outcome_(RacAttemptOutcome::PARSE_ERROR);
    }
    if (this->current_message_ == this->rac_wifi_status_message_) {
      this->rac_wifi_status_outcome_ = RacAttemptOutcome::PARSE_ERROR;
    }
    if (this->current_message_ == this->rac_premium_poll_message_) {
      this->rac_premium_poll_outcome_ = RacAttemptOutcome::PARSE_ERROR;
    }
    if (this->current_message_->set_state(Message::State::INVALID) == Message::State::EXPIRED) {
      ESP_LOGE(TAG, "RECEIVE: expired");
    } else {
      // Transmission consumes the request view. A retry must expose the entire
      // immutable frame again or FORMATTED would immediately send zero bytes.
      this->current_message_->request_buffer()->reset_view();
      this->current_message_->set_state(Message::State::FORMATTED);
      ESP_LOGW(TAG, "RECEIVE: failed, retransmitting");
    }
  };

  if (!this->buffer_rx_.free()) {
    ESP_LOGE(TAG, "RECEIVE: buffer_rx full without a complete frame");
    retry_or_expire();
    return;
  }

  int available_bytes = 0;
  size_t len = 0;
  bool read_ok = true;

  // The pinned ArduinoCore-API RingBuffer uses a shared element counter:
  // store_char() increments it in the UART ISR and read_char() decrements it
  // here. Those read-modify-write operations are not atomic on AmebaZ. Once
  // their race corrupts the counter, RX never self-heals although TX remains
  // fully operational. Mask only UART0's interrupt for the very short software
  // buffer drain; bytes arriving meanwhile remain in the hardware FIFO.
#if defined(USE_LIBRETINY) && defined(HLINK2_UART_RX_IRQ_GUARD)
  hlink2_uart0_rx_critical_enter();
#endif
  available_bytes = this->available();
  if (available_bytes > 0) {
    len = std::min(this->buffer_rx_.free(), static_cast<size_t>(available_bytes));
    read_ok = this->read_array(reinterpret_cast<uint8_t*>(this->buffer_rx_.next()), len);
  }
#if defined(USE_LIBRETINY) && defined(HLINK2_UART_RX_IRQ_GUARD)
  hlink2_uart0_rx_critical_exit();
#endif

  if (available_bytes <= 0) {
    // Never wait for UART bytes in the high-priority Arduino task.
    return;
  }

  if (static_cast<size_t>(available_bytes) > len) {
    ESP_LOGE(TAG, "RECEIVE: buffer_rx too small, truncating read at %zu bytes", len);
  }
  ESP_LOGV(TAG, "RECEIVE: %zu bytes to read", len);
  if (!read_ok) {
    ESP_LOGE(TAG, "RECEIVE: failed to read");
    return;
  }

  this->buffer_rx_.set_size(this->buffer_rx_.size() + len);
  this->buffer_rx_.update();

  switch (this->buffer_rx_.state()) {
    case IOBuffer::State::READY:
      ESP_LOGV(TAG, "RECEIVE: @%p: done (%zu bytes)", this->current_message_, this->buffer_rx_.size());
      this->current_message_->set_state(Message::State::RECEIVED);
      return;
    case IOBuffer::State::INVALID:
      retry_or_expire();
      return;
    case IOBuffer::State::EMPTY:
    case IOBuffer::State::PARTIAL:
      // A frame spans many 9600-baud UART interrupts. Continue on a later
      // ESPHome pass after lower-priority networking tasks have run.
      return;
  }
}


void Core::task_parse() {
  ESP_LOGV(TAG, "PARSE: start");
  switch(this->current_message_->parse(this->buffer_rx_)) {
    case Message::State::PARSED:
      ESP_LOGV(TAG, "PARSE: done, %d mnemonics to process", this->current_message_->response_mnemonics.size());

      if (
        this->current_message_->flag->match_mode(Mnemonic::Mode::CMD)
        && !this->current_message_->accepts_any_checksummed_response()
        && *this->current_message_->response == Message::Response::VALID
        && this->current_message_->size() > 0
      ){
        ESP_LOGV(TAG, "PARSE: @%p: use command values", this->current_message_);
        this->current_message_->apply_requests();
      }

      if (
        this->current_message_->response_mnemonics.empty()
        && !this->current_message_->accepts_any_checksummed_response()
        && !this->current_message_->tracks_checksummed_response()
      ) {
        ESP_LOGI(TAG, "PARSE: @%p: drop (empty)", this->current_message_);
        this->current_message_->set_state(Message::State::PROCESSED);
        this->clear_current_message();
        return;
      }
      if (!this->received_messages.push_back(this->current_message_)) {
        ESP_LOGE(TAG, "PARSE: received queue full, dropping @%p", this->current_message_);
        this->current_message_->set_state(Message::State::EXPIRED);
      }
      this->clear_current_message();
      return;
    case Message::State::EXPIRED:
      ESP_LOGW(TAG, "PARSE: expired");
      return;
    default:
      if (this->current_message_ == this->rac_expected_message_) {
        this->set_rac_current_outcome_(RacAttemptOutcome::PARSE_ERROR);
      }
      if (this->current_message_ == this->rac_wifi_status_message_) {
        this->rac_wifi_status_outcome_ = RacAttemptOutcome::PARSE_ERROR;
      }
      if (this->current_message_ == this->rac_premium_poll_message_) {
        this->rac_premium_poll_outcome_ = RacAttemptOutcome::PARSE_ERROR;
      }
      this->current_message_->request_buffer()->reset_view();
      this->current_message_->set_state(Message::State::FORMATTED);
      ESP_LOGW(TAG, "PARSE: failed, retransmitting");
      return;
  }
}


void Core::task_process() {
  ESP_LOGV(TAG, "PROCESS: start, %d messages to process", this->received_messages.size());
  if (this->received_messages.empty()) {
    return;
  }

  Message* msg = this->received_messages.front();
  const auto finish = [this, msg](bool run_message_callbacks) {
    if (run_message_callbacks) {
      msg->run_callbacks();
    }
    msg->response_mnemonics.clear();
    if (msg->flag->match_mode(Mnemonic::Mode::CMD)) {
      msg->clear_requests();
    }
    // Persistent messages become schedulable again; ephemeral messages are
    // garbage-collected by task_schedule(). Never leave a dropped response in
    // PARSED, because the scheduler intentionally does not select that state.
    msg->set_state(Message::State::PROCESSED);
    this->received_messages.pop_front();
  };

  if (!msg->response) {
    ESP_LOGW(TAG, "PROCESS: @%p (%s) dropped, no response", msg, msg->flag->raw);
    finish(false);
    return;
  }

  // RAC startup needs a transport-level completion signal: after framing and
  // checksum succeeded, run only the Message callback and retain the raw Res.
  // Do not publish mnemonic values from INVALID/EMPTY replies.
  if (msg->accepts_any_checksummed_response()) {
    ESP_LOGV(
      TAG,
      "PROCESS: @%p: checksum-valid response Res=%u (frame-only policy)",
      msg,
      static_cast<unsigned>(*msg->response)
    );
    finish(true);
    return;
  }

  switch (*msg->response) {
    case Message::Response::VALID:
      ESP_LOGV(TAG, "PROCESS: @%p: response VALID", msg);
      break;
    case Message::Response::PARTIAL:
      ESP_LOGW(TAG, "PROCESS: @%p: response PARTIAL", msg);
      break;
    case Message::Response::INVALID:
      ESP_LOGW(TAG, "PROCESS: @%p: response INVALID", msg);
      finish(msg->tracks_checksummed_response());
      return;
    case Message::Response::EMPTY:
      ESP_LOGW(TAG, "PROCESS: @%p: response EMPTY", msg);
      finish(msg->tracks_checksummed_response());
      return;
    default:
      ESP_LOGW(TAG, "PROCESS: @%p: dropped, response unknown (%u)", msg, *msg->response);
      finish(msg->tracks_checksummed_response());
      return;
  }

  // Process one complete response snapshot, but never batch multiple messages
  // or spin against a time budget. Climate::control derives an outgoing command
  // from several fields published by these callbacks, so splitting one STS
  // frame across global ESPHome passes would expose a mixed old/new snapshot.
  while (!msg->response_mnemonics.empty()) {
    Mnemonic* mnemonic = msg->response_mnemonics.front();
    ESP_LOGVV(TAG, "PROCESS: @%p: processing %s", msg, mnemonic->name);
    mnemonic->run_callbacks();
    msg->response_mnemonics.pop_front();
    ESP_LOGVV(TAG, "PROCESS: @%p: %s done", msg, mnemonic->name);
  }

  ESP_LOGV(TAG, "PROCESS: @%p: done", msg);
  finish(true);
  return;
}

} // hlink2
} //esphome
