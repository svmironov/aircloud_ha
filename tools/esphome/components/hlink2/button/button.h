#pragma once

#include "esphome/components/button/button.h"

#include "../core.h"
#include "../component.h"
#include "esphome/core/helpers.h"
#include <cstring>


namespace esphome {
namespace hlink2 {

#ifndef CONF_BUTTON_RAW
  #define CONF_BUTTON_RAW CONF_MESSAGE_CMD_RAW
#endif


class Button: public button::Button, public CommandComponent {
  public:
    static constexpr const char TAG[] = "hlink2:button";
    static constexpr const bool RAW = CONF_BUTTON_RAW;

    void setup() override {
      CommandComponent::setup();
    }

    void dump_config() override{
      CommandComponent::dump_config_<TAG>(this->name_.c_str());
    }


    void set_mnemonic(Mnemonic* m, const char* value, MessageParameters params = {}, bool raw = RAW) {
      CommandComponent::set_mnemonic(m, nullptr, params);
      memcpy(this->value_, value, std::strlen(value));
      this->raw_ = raw;
    }

    /// Set mnemonic attached to the object with default callback. Called from Python
    inline void set_mnemonic_default(Mnemonic* m, MessageParameters params = {}, bool raw = RAW) {
      set_mnemonic(m, "1", params, raw);
    }

    void press_action() override {
      this->request_->set_request(this->value_, this->raw_);
      this->get_parent()->schedule_message(this->message_);
    }

  protected:
    char value_[MNEMONIC_BUFFER_SIZE] = "";
    bool raw_{CONF_MESSAGE_CMD_RAW};

};


class UpdateButton: public button::Button, public Parented<Core> {
  void press_action() override {
    this->get_parent()->force_update_messages();
  }
}; 


} // hlink2
} //esphome