#pragma once

#include "esphome/core/component.h"

#include "./core.h"
#include "./mnemonics.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"
#include "main.h"
#include "message.h"
#include <cstdint>
#include <utility>


namespace esphome {
namespace hlink2 {


class StatusComponent: public virtual Component, public virtual Parented<Core> {
  public:
    void setup() override {
      if (!this->mnemonic_ || !this->parameters_.update_interval) {
        this->mark_failed("set_mnemonic not called");
        return;
      }
      if (!this->get_parent()) {
        this->mark_failed("get_parent failed");
        return;
      }
      if (!(this->message_ = this->get_parent()->register_status_mnemonic(*this->mnemonic_, this->parameters_, this->promote_))) {
        std::string report = "register_status_mnemonic failed ";
        report += this->mnemonic_->name;
        this->mark_failed(report.c_str());

      }
    }

    /// empty method required because register_component calls it in python
    inline void set_update_interval(uint32_t interval) {}//{ this->parameters_.update_interval = interval; };

    template<typename FUNC, uint32_t UPDATE_INTERVAL=MESSAGE_UPDATE_INTERVAL>
    void set_mnemonic(Mnemonic* m, FUNC&& callback, MessageParameters params, bool promote = CONF_MESSAGE_STS_PROMOTE) {
      if (!m) {
        this->mark_failed("invalid mnemonic");
        return;
      }
      this->mnemonic_ = m;
      this->parameters_ = params;
      this->parameters_.update_interval = params.update_interval.value_or(UPDATE_INTERVAL);
      this->promote_ = promote;
      if constexpr( (!std::is_same_v<std::decay_t<FUNC>, std::nullptr_t>) ) {
        m->add_callback(std::forward<FUNC>(callback));
      }
    }

  inline Message*& message() { return this->message_; }
  
  protected:
    template<const char* TAG>
    void dump_config_(const char* name) {
      ESP_LOGCONFIG(TAG,
        "'%s': @%p: mnemonic=%s dest=%s interval=%ums promote=%s",
        name,
        this->message_,
        this->mnemonic_->name,
        Mnemonic::DestToString(this->mnemonic_->dest),
        this->message_->interval().delay(),
        YESNO(this->promote_)
      );
    }

    Message* message_{nullptr};
    Mnemonic* mnemonic_{nullptr};
    MessageParameters parameters_{};
    bool promote_{true};
};


/// Pure command component (no status update)
class CommandComponent: public virtual Component, public virtual Parented<Core> {
  public:
    void setup() override {
      if (!this->mnemonic_) {
        this->mark_failed("set_mnemonic not called");
        return;
      }
      if (!this->get_parent()) {
        this->mark_failed("get_parent failed");
        return;
      }
      switch (this->mnemonic_->dest) {
        case Mnemonic::Dest::IDU:
          this->message_ = this->get_parent()->register_persistent_message<Mnemonic::Mode::CMD, Mnemonic::Dest::IDU>(this->parameters_);
          break;
        case Mnemonic::Dest::ODU:
          this->message_ = this->get_parent()->register_persistent_message<Mnemonic::Mode::CMD, Mnemonic::Dest::ODU>(this->parameters_);
          break;
        default:;
      }
      if (!this->message_) {
        std::string report = "register_command_mnemonic failed ";
        report += this->mnemonic_->name;
        this->mark_failed(report.c_str());
        return;
      }
      this->request_ = this->message_->add(*this->mnemonic_);

      // status handle
      MessageParameters params{};
      if (this->parameters_.update_interval) {
        params.update_interval = this->parameters_.update_interval;
      }
      if (this->mnemonic_->match_mode(Mnemonic::Mode::STS)) {
        if (Message* msg = this->get_parent()->register_status_mnemonic(*this->mnemonic_, {}, true)) {
          this->message_->add_callback([msg]() { msg->interval().force_expiration(); });
        }
      }
    }

    template<typename FUNC>
    void set_mnemonic(Mnemonic* m, FUNC&& callback, MessageParameters params) {
      if (!m) {
        this->mark_failed("invalid mnemonic");
        return;
      }
      this->mnemonic_ = m;
      this->parameters_ = params;
      if constexpr( (!std::is_same_v<std::decay_t<FUNC>, std::nullptr_t>) ) {
        if (m->match_mode(Mnemonic::Mode::STS)) {
          m->add_callback(std::forward<FUNC>(callback));
        }
      }
      
    }
  
    inline Message*& message() { return this->message_; }

  protected:
    template<const char* TAG>
    void dump_config_(const char* name) {
      ESP_LOGCONFIG(TAG,
        "'%s': @%p: mnemonic=%s dest=%s buzzer=%s",
        name,
        this->message_,
        this->mnemonic_->name,
        Mnemonic::DestToString(this->mnemonic_->dest),
        YESNO(*this->parameters_.buzzer)
      );
    }

    Message* message_{nullptr};
    Mnemonic* mnemonic_{nullptr};
    Request* request_{nullptr};
    MessageParameters parameters_{};
};

}
}