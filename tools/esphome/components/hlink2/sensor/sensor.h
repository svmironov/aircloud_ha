#pragma once

#include "esphome/components/sensor/sensor.h"

#include "../core.h"
#include "../component.h"

namespace esphome {
namespace hlink2 {

#ifndef CONF_SENSOR_UPDATE_INTERVAL
  #define CONF_SENSOR_UPDATE_INTERVAL MESSAGE_UPDATE_INTERVAL
#endif
#ifndef CONF_SENSOR_PROMOTE
  #define CONF_SENSOR_PROMOTE CONF_MESSAGE_STS_PROMOTE
#endif


class Sensor: public sensor::Sensor, public StatusComponent {
  public:
    static constexpr const char TAG[] = "hlink2:sensor";
    static constexpr const uint32_t UPDATE_INTERVAL = CONF_SENSOR_UPDATE_INTERVAL; 
    static constexpr const bool PROMOTE = CONF_SENSOR_PROMOTE;

    void dump_config() override{
      StatusComponent::dump_config_<TAG>(this->name_.c_str());
    }

    template<typename FUNC>
    void set_mnemonic(Mnemonic* m, FUNC&& callback, MessageParameters params = {}, bool promote = PROMOTE) {
      StatusComponent::set_mnemonic<FUNC, UPDATE_INTERVAL>(m, std::forward<FUNC>(callback), params, promote);
    }

    /// Set mnemonic attached to the object with default callback. Called from Python
    void set_mnemonic_default(Mnemonic* m, MessageParameters params = {}, bool promote = PROMOTE) {
      this->set_mnemonic( m,[this, m]() { this->publish_state(m->get_status<float>()); }, params, promote);
    }
};


} // hlink2
} //esphome