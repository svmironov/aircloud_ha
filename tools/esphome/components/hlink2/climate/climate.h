#pragma once

#include "esphome/components/climate/climate_mode.h"
#include "esphome/core/component.h"
#include "esphome/components/climate/climate.h"

#include "../core.h"
#include <cstddef>
#include <cstdint>
#include <set>
#include <string>
#include <vector>

namespace esphome {
namespace hlink2 {


#ifndef CONF_CLIMATE_UPDATE_INTERVAL
  #define CONF_CLIMATE_UPDATE_INTERVAL MESSAGE_UPDATE_INTERVAL
#endif 


constexpr uint32_t CLIMATE_UPDATE_INTERVAL = CONF_CLIMATE_UPDATE_INTERVAL; 


class Climate: public Component, public climate::Climate, public Parented<Core> {
  public:
    enum ClimateMode: uint16_t {
      CLIMATE_MODE_HEAT_COOL = 33024,
      CLIMATE_MODE_COOL = 64,
      CLIMATE_MODE_HEAT = 16,
      CLIMATE_MODE_FAN_ONLY = 81,
      CLIMATE_MODE_DRY = 33,
      CLIMATE_MODE_AUTO = 0xffff,
    };

    enum ClimateAction: uint16_t {
      CLIMATE_ACTION_OFF = 0,
      CLIMATE_ACTION_COOLING = 64,
      CLIMATE_ACTION_HEATING = 16,
      CLIMATE_ACTION_IDLE = 0,
      CLIMATE_ACTION_DRYING = 33,
      CLIMATE_ACTION_FAN = 81,
    };

    enum ClimateFanMode: uint8_t {
      CLIMATE_FAN_AUTO = 0,
      CLIMATE_FAN_QUIET = 4,
      CLIMATE_FAN_LOW = 3,
      CLIMATE_FAN_MEDIUM = 2,
      CLIMATE_FAN_MIDDLE = 1,
      CLIMATE_FAN_HIGH = 5,
    };

    enum ClimateSwingMode : uint8_t {
      CLIMATE_SWING_OFF = 0,
      CLIMATE_SWING_BOTH = 3,
      CLIMATE_SWING_VERTICAL = 1,
      CLIMATE_SWING_HORIZONTAL = 2,
    };

  /// Enum for all preset modes MSB> OPT1|OPT2|OPT3|OPT4 <LSB (LSB first in memory because RTL8710BN is litte-endian)
    enum ClimatePreset : uint32_t {
      /// No preset is active
      CLIMATE_PRESET_NONE = 0, // OPT1 + OPT4
      CLIMATE_PRESET_AWAY = 1, // OPT4
      CLIMATE_PRESET_BOOST = 64, // OPT4
      CLIMATE_PRESET_ECO = (1<<24), // OPT1
      CLIMATE_PRESET_SILENCE = 128, // OPT4
      CLIMATE_PRESET_SLEEP = (64<< 8) + 128,
    };

    static constexpr const char CLIMATE_CUSTOM_PRESET_SILENCE[] = "Silence";


    void setup() override;
    void dump_config() override;
    
    void control(const climate::ClimateCall &call) override;
    climate::ClimateTraits traits() override;
    void set_supported_modes(const std::set<climate::ClimateMode> &modes);
    void set_supported_swing_modes(const std::set<climate::ClimateSwingMode> &modes);
    void set_supported_fan_modes(const std::set<climate::ClimateFanMode> &modes);
    void set_supported_presets(const std::set<climate::ClimatePreset> &presets);
    void set_supported_custom_presets(const std::set<std::string> &presets);
    void set_supports_hvac_actions(bool support_hvac_actions);
  
    /// set status message parameters
    void set_message_status_parameters(MessageParameters params = {});
    void set_message_command_parameters(MessageParameters params = {});

    /// empty method required because register_component calls it in python
    inline void set_update_interval(uint32_t interval) {};

    void set_power();

    void set_mode(uint16_t);
    inline void set_mode() { set_mode(Mnemonic::IDU_Mode.get_status<uint16_t>()); };
    
    void set_real_mode(uint16_t);
    inline void set_real_mode() { set_real_mode(Mnemonic::IDU_RlMd.get_status<uint16_t>()); };

    void set_fan_speed(uint8_t);
    inline void set_fan_speed() { set_fan_speed(Mnemonic::IDU_FanS.get_status<uint8_t>()); };

    void set_fan_swing(uint8_t);
    inline void set_fan_swing() { set_fan_swing(Mnemonic::IDU_FanSw.get_status<uint8_t>()); };

    void set_target_temperature(float);
    inline void set_target_temperature() { set_target_temperature(Mnemonic::IDU_SetT.get_status<float>()); }

    void set_current_temperature(float);
    inline void set_current_temperature() { set_current_temperature(Mnemonic::IDU_Tr.get_status<float>()); }

    void set_current_humidity(uint8_t);
    inline void set_current_humidity() { set_current_humidity(Mnemonic::IDU_Hr.get_status<uint8_t>()); }

    void set_preset(uint32_t value);
    void set_preset();

  protected:
    climate::ClimateTraits traits_ = climate::ClimateTraits();
    // ESPHome stores custom-preset names as const char pointers. Keep the
    // backing strings alive for as long as the climate entity exists.
    std::vector<std::string> custom_presets_storage_;
    Message* status_;
    Message* control_;
    MessageParameters status_params_;
    MessageParameters control_params_;

  Request* request_OnOf{nullptr};
  Request* request_Mode{nullptr};
  Request* request_FanS{nullptr};
  Request* request_FanSw{nullptr};
  Request* request_SetT{nullptr};
  Request* request_Opt1{nullptr};
  Request* request_Opt2{nullptr};
  Request* request_Opt3{nullptr};
  Request* request_Opt4{nullptr};
};


} // hlink2
} //esphome
