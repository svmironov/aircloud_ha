#pragma once

#include "esphome/components/number/number.h"

#include "../core.h"
#include "../component.h"

namespace esphome {
namespace hlink2 {


class Number: public number::Number, public CommandComponent {
  public:
    static constexpr const char TAG[] = "hlink2:number";

    void setup() override {
      CommandComponent::setup();
    }

    void dump_config() override{
      CommandComponent::dump_config_<TAG>(this->name_.c_str());
    }

    template<typename FUNC>
    void set_mnemonic(Mnemonic* m, FUNC&& callback, MessageParameters params = {}) {
      CommandComponent::set_mnemonic<FUNC>(m, std::forward<FUNC>(callback), params);
    }

    /// Set mnemonic attached to the object with default callback. Called from Python
    void set_mnemonic_default(Mnemonic* m, MessageParameters params = {}) {
      this->set_mnemonic(m, [this]() { this->apply_state(); }, params);
    }

    void control(float value) override {
      this->request_->set_request<float>(value);
      this->get_parent()->schedule_message(this->message_);
      this->publish_state(value);
    }

    inline void apply_state() {
      this->publish_state(this->mnemonic_->get_status<float>());
    }
};


}
}