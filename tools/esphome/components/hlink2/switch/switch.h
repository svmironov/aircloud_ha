#pragma once

#include "esphome/components/switch/switch.h"

#include "../core.h"
#include "../component.h"
#include "esphome/core/helpers.h"


namespace esphome {
namespace hlink2 {


class Switch: public switch_::Switch, public CommandComponent {
  public:
    static constexpr const char TAG[] = "hlink2:switch";

    void setup() override {
      CommandComponent::setup();
      bool initial_state = this->get_initial_state_with_restore_mode().value_or(false);
      this->publish_state(initial_state);
    }

    void dump_config() override{
      CommandComponent::dump_config_<TAG>(this->name_.c_str());
    }

    /// Set mnemonic attached to the object with default callback. Called from Python
    void set_mnemonic_default(Mnemonic* m, MessageParameters params = {}) {
      set_mnemonic( m,[this]() { this->apply_state(); }, params);
    }

    void write_state(bool state) override {
      this->request_->set_request(state ? '1' : '0');
      this->get_parent()->schedule_message(this->message_);
    }

    /// apply mnemonic boolean state
    inline void apply_state() {
      if (this->mnemonic_->match_mode(Mnemonic::Mode::STS)) {
        switch_::Switch::publish_state(this->mnemonic_->get_status<bool>());
      }
    }
};

class BuzzerSwitch: public switch_::Switch, public virtual Component, public virtual Parented<Core> {
  public:
    void setup() override {
      this->state_ = this->get_initial_state_with_restore_mode().value_or(false);
      this->publish_state(this->state_);
    }

    void write_state(bool state) override {
      this->state_ = state;
      this->get_parent()->buzzer(state);
      this->publish_state(state);
    }

  protected:
    bool state_{false};
};

} // hlink2
} //esphome