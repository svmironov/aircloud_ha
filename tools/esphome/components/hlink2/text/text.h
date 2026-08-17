#pragma once

#include "esphome/components/text/text.h"

#include "../core.h"
#include "../component.h"
#include "esphome/core/log.h"

namespace esphome {
namespace hlink2 {


#ifndef CONF_TEXT_RAW
  #define CONF_TEXT_RAW CONF_MESSAGE_CMD_RAW
#endif

class Text: public text::Text, public CommandComponent {
  public:
    static constexpr const char TAG[] = "hlink2:text";
    static constexpr const bool RAW = CONF_TEXT_RAW;

    void setup() override {
      CommandComponent::setup();
    }

    void dump_config() override{
      CommandComponent::dump_config_<TAG>(this->name_.c_str());
    }

    template<typename FUNC>
    void set_mnemonic(Mnemonic* m, FUNC&& callback, MessageParameters params = {}, bool raw = RAW) {
      CommandComponent::set_mnemonic<FUNC>(m, std::forward<FUNC>(callback), params);
      this->raw_ = raw;
    }

    /// Set mnemonic attached to the object with default callback. Called from Python
    void set_mnemonic_default(Mnemonic* m, MessageParameters params = {}, bool raw = RAW) {
      this->set_mnemonic(m, [this]() { this->apply_state(); }, params, raw);
    }

    void control(const std::string &value) override {
      if (!this->request_->set_request(value, this->raw_)) {
        ESP_LOGW(TAG, "control: truncated (%zu/%zu)", this->request_->view().size(), value.size());
      }

      this->get_parent()->schedule_message(this->message_);
      this->publish_state(value);
    }

    inline void apply_state() {
      this->publish_state(std::string(this->mnemonic_->get_status<std::string_view>()));
    }

  protected:
    bool raw_{false};
};


}
}