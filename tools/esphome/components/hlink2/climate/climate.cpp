#include "esphome/components/climate/climate.h"
#include "esphome/components/climate/climate_mode.h"

#include <cstdint>
#include <optional>

#include "climate.h"
#include "../core.h"
#include "esphome/core/log.h"

namespace esphome {
namespace hlink2 {


static const char *const TAG = "hlink2:climate";


void Climate::setup() {
  if (!this->get_parent()) {
    this->mark_failed("get_parent failed");
    return;
  }
  if (!(status_ = this->get_parent()->register_persistent_message<Mnemonic::Mode::STS, Mnemonic::Dest::IDU>(this->status_params_))) {
    this->mark_failed("register_status_message failed");
    return;
  }

  status_->add(Mnemonic::IDU_OnOf);
  status_->add(Mnemonic::IDU_Mode);
  status_->add(Mnemonic::IDU_RlMd);
  status_->add(Mnemonic::IDU_FanS);
  status_->add(Mnemonic::IDU_FanSw);
  status_->add(Mnemonic::IDU_SetT);
  status_->add(Mnemonic::IDU_Tr);
  status_->add(Mnemonic::IDU_Hr);
  // Opt1..Opt4 carry preset state only. Polling them pushes the status request to
  // 12 mnemonics, and the indoor unit then answers Res:3 (PARTIAL): it returns some
  // requested fields and silently drops others. Callbacks run per returned mnemonic,
  // so a reply missing OnOf never calls set_power() -- the one place mode and action
  // are derived -- and the entity kept reporting COOL/COOLING after the unit was
  // switched off, while Tr and Hr in the same reply carried on updating. Ask for
  // these four only when a preset is actually configured.
  if (this->traits_.get_supports_presets() || !this->traits_.get_supported_custom_presets().empty()) {
    status_->add(Mnemonic::IDU_Opt1);
    status_->add(Mnemonic::IDU_Opt2);
    status_->add(Mnemonic::IDU_Opt3);
    status_->add(Mnemonic::IDU_Opt4);
  }
  
  Mnemonic::IDU_OnOf.add_callback([this]() {this->set_power();}); // OnOff triggers RlMd and Mode
  Mnemonic::IDU_FanS.add_callback([this]() {this->set_fan_speed();});
  Mnemonic::IDU_FanSw.add_callback([this]() {this->set_fan_swing();});
  Mnemonic::IDU_SetT.add_callback([this]() {this->set_target_temperature();});
  Mnemonic::IDU_Tr.add_callback([this]() {this->set_current_temperature();});
  Mnemonic::IDU_Hr.add_callback([this]() {this->set_current_humidity();});

  status_->add_callback([this]() { this->set_preset(); this->publish_state(); });
  this->get_parent()->add_rac_premium_snapshot_callback(
    [this]() { this->set_preset(); this->publish_state(); }
  );

  if(!(this->control_ = this->get_parent()->register_persistent_message<Mnemonic::Mode::CMD, Mnemonic::Dest::IDU>(this->control_params_)) ) {
    this->mark_failed("register_command_message failed");
    return;
  }
  this->request_OnOf = this->control_->add(Mnemonic::IDU_OnOf);
  this->request_Mode = this->control_->add(Mnemonic::IDU_Mode);
  this->request_FanS = this->control_->add(Mnemonic::IDU_FanS);
  this->request_FanSw = this->control_->add(Mnemonic::IDU_FanSw);
  this->request_SetT = this->control_->add(Mnemonic::IDU_SetT);
  this->request_Opt1 = this->control_->add(Mnemonic::IDU_Opt1);
  this->request_Opt2 = this->control_->add(Mnemonic::IDU_Opt2);
  this->request_Opt3 = this->control_->add(Mnemonic::IDU_Opt3);
  this->request_Opt4 = this->control_->add(Mnemonic::IDU_Opt4);
  this->control_->add_callback([this]() { this->publish_state(); });
}


void Climate::dump_config() {
  ESP_LOGCONFIG(TAG, "Climate '%s'", this->name_.c_str());
  ESP_LOGCONFIG(TAG, " %s", this->status_->config().c_str());
  ESP_LOGCONFIG(TAG, " %s", this->control_->config().c_str());
}


void Climate::set_message_status_parameters(MessageParameters params) {
  params.update_interval = params.update_interval.value_or(CLIMATE_UPDATE_INTERVAL);
  this->status_params_ = params;
}

void Climate::set_message_command_parameters(MessageParameters params) {
  this->control_params_ = params;
}


void Climate::set_power() {
  const char power = Mnemonic::IDU_OnOf.get_status<char>();
  if (power == '0') {
    ESP_LOGV(TAG, "climate power: OFF");
    this->set_mode(0);
    this->set_real_mode(Climate::CLIMATE_ACTION_OFF);
  } else {
    ESP_LOGV(TAG, "climate power: ON");
    this->set_mode(Mnemonic::IDU_Mode.get_status<uint16_t>());
    this->set_real_mode(Mnemonic::IDU_RlMd.get_status<uint16_t>());
  }
}

void Climate::set_preset() {
  set_preset( 
    (Mnemonic::IDU_Opt1.get_status<uint8_t>(0)<<24)
    + (Mnemonic::IDU_Opt2.get_status<uint8_t>(0)<<16)
    + (Mnemonic::IDU_Opt3.get_status<uint8_t>(0)<<8)
    + Mnemonic::IDU_Opt4.get_status<uint8_t>(0)
  );
}

void Climate::set_preset(uint32_t value) {
  /// this implementation doesn't allow multiple values at once, a bitmask test could be a better solution (but doesn't fit with presets)
  this->preset.reset();
  this->clear_custom_preset_();
  switch (value) {
    case CLIMATE_PRESET_AWAY:
      this->preset = climate::CLIMATE_PRESET_AWAY;
      ESP_LOGV(TAG, "set_preset: AWAY");
      break;
    case CLIMATE_PRESET_BOOST:
      this->preset = climate::CLIMATE_PRESET_BOOST;
      ESP_LOGV(TAG, "set_preset: BOOST");
      break;
    case CLIMATE_PRESET_ECO:
      this->preset = climate::CLIMATE_PRESET_ECO;
      ESP_LOGV(TAG, "set_preset: ECO");
      break;
    case CLIMATE_PRESET_SILENCE:
      this->set_custom_preset_(CLIMATE_CUSTOM_PRESET_SILENCE);
      ESP_LOGV(TAG, "set_preset: SILENCE");
      break;
    case CLIMATE_PRESET_SLEEP:
      this->preset = climate::CLIMATE_PRESET_SLEEP;
      ESP_LOGV(TAG, "set_preset: SLEEP");
      break;
    case CLIMATE_PRESET_NONE:
      this->preset = climate::CLIMATE_PRESET_NONE;
      ESP_LOGV(TAG, "set_preset: NONE (%lu)", value);
      break;
    default:
      this->preset = climate::CLIMATE_PRESET_NONE;
      ESP_LOGW(TAG, "set_preset: unknow preset %lu", value);
  }
}

void Climate::set_mode(uint16_t value) {
  switch(value) {
    case Climate::CLIMATE_MODE_HEAT_COOL:
      this->mode = climate::ClimateMode::CLIMATE_MODE_HEAT_COOL;
      ESP_LOGV(TAG, "climate mode: HEAT/COOL (%u)", value);
      break;
    case Climate::CLIMATE_MODE_COOL:
      this->mode = climate::ClimateMode::CLIMATE_MODE_COOL;
      ESP_LOGV(TAG, "climate mode: COOL (%u)", value);
      break;
    case Climate::CLIMATE_MODE_HEAT:
      this->mode = climate::ClimateMode::CLIMATE_MODE_HEAT;
      ESP_LOGV(TAG, "climate mode: HEAT (%u)", value);
      break;
    case Climate::CLIMATE_MODE_FAN_ONLY:
      this->mode = climate::ClimateMode::CLIMATE_MODE_FAN_ONLY;
      ESP_LOGV(TAG, "climate mode: FAN (%u)", value);
      break;
    case Climate::CLIMATE_MODE_DRY:
      this->mode = climate::ClimateMode::CLIMATE_MODE_DRY;
      ESP_LOGV(TAG, "climate mode: DRY (%u)", value);
      break;
    case Climate::CLIMATE_MODE_AUTO:
      this->mode = climate::ClimateMode::CLIMATE_MODE_AUTO;
      ESP_LOGV(TAG, "climate mode: AUTO (%u)", value);
      break;
    case 0:
      ESP_LOGV(TAG, "climate mode: OFF (%u)", value);
      this->mode = climate::CLIMATE_MODE_OFF;
      break;
    default:
      ESP_LOGW(TAG, "climate mode: UNKNOWN (%u)", value);
  }
}


void Climate::set_real_mode(uint16_t value) {
  switch(value & 0xff) {
    case Climate::CLIMATE_ACTION_OFF:
      this->action = climate::ClimateAction::CLIMATE_ACTION_OFF;
      ESP_LOGV(TAG, "climate action: OFF (%u)", value);
      break;
    case Climate::CLIMATE_ACTION_HEATING:
      this->action = climate::ClimateAction::CLIMATE_ACTION_HEATING;
      ESP_LOGV(TAG, "climate action: HEATING (%u)", value);
      break;
    case Climate::CLIMATE_ACTION_COOLING:
      this->action = climate::ClimateAction::CLIMATE_ACTION_COOLING;
      ESP_LOGV(TAG, "climate action: COOLING (%u)", value);
      break;
    case Climate::CLIMATE_ACTION_DRYING:
      this->action = climate::ClimateAction::CLIMATE_ACTION_DRYING;
      ESP_LOGV(TAG, "climate action: DRYING (%u)", value);
      break;
    case Climate::CLIMATE_ACTION_FAN:
      this->action = climate::ClimateAction::CLIMATE_ACTION_FAN;
      ESP_LOGV(TAG, "climate action: FAN (%u)", value);
      break;
    default:
      ESP_LOGW(TAG, "climate action: UNKNOWN (%u)", value);
  }
}


void Climate::set_fan_speed(uint8_t value) {
  switch(value) {
    case Climate::CLIMATE_FAN_AUTO:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_AUTO;
      ESP_LOGV(TAG, "fan speed: AUTO (%d)", value);
      break;
    case Climate::CLIMATE_FAN_QUIET:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_QUIET;
      ESP_LOGV(TAG, "fan speed: QUIET (%d)", value);
      break;
    case Climate::CLIMATE_FAN_LOW:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_LOW;
      ESP_LOGV(TAG, "fan speed: LOW (%d)", value);
      break;
    case Climate::CLIMATE_FAN_MEDIUM:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_MEDIUM;
      ESP_LOGV(TAG, "fan speed: MEDIUM (%d)", value);
      break;
    case Climate::CLIMATE_FAN_MIDDLE:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_MIDDLE;
      ESP_LOGV(TAG, "fan speed: MIDDLE (%d)", value);
      break;
    case Climate::CLIMATE_FAN_HIGH:
      this->fan_mode = climate::ClimateFanMode::CLIMATE_FAN_HIGH;
      ESP_LOGV(TAG, "fan speed: HIGH (%d)", value);
      break;
    default:
      ESP_LOGW(TAG, "fan speed: UNKNOWN (%d)", value);
      return;
  }
}


void Climate::set_fan_swing(uint8_t value) {
  switch(value) {
    case Climate::CLIMATE_SWING_OFF:
      this->swing_mode = climate::ClimateSwingMode::CLIMATE_SWING_OFF;
      ESP_LOGV(TAG, "swing mode: OFF (%u)", value);
      break;
    case Climate::CLIMATE_SWING_VERTICAL:
      this->swing_mode = climate::ClimateSwingMode::CLIMATE_SWING_VERTICAL;
      ESP_LOGV(TAG, "swing mode: VERTICAL (%u)", value);
      break;
    default:
      ESP_LOGW(TAG, "swing mode: UNKNOWN (%u)", value);
      return;
  }
}


void Climate::set_target_temperature(float value) {
  this->target_temperature = value;
  ESP_LOGV(TAG, "target temperature: %.1f", value);
}


void Climate::set_current_temperature(float value) {
  this->current_temperature = value;
  ESP_LOGV(TAG, "current temperature: %.1f", value);
}


void Climate::set_current_humidity(uint8_t value) {
  this->current_humidity = static_cast<float>(value);
  ESP_LOGV(TAG, "current humidity: %d", value);
}


void Climate::control(const climate::ClimateCall &call) {
  if (!this->control_) {
    ESP_LOGE(TAG, "control: invalid command message");
    return;
  }

  switch( call.get_mode() ? *call.get_mode() : this->mode ) {
    case climate::ClimateMode::CLIMATE_MODE_OFF:
      this->request_OnOf->set_request('0');
      this->request_Mode->set_request(Mnemonic::IDU_Mode.get_status('0'));
      ESP_LOGV(TAG, "CONTROL: mode -> OFF");
      break;
    case climate::ClimateMode::CLIMATE_MODE_HEAT_COOL:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_HEAT_COOL>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> HEAT/COOL [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    case climate::ClimateMode::CLIMATE_MODE_COOL:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_COOL>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> COOL [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    case climate::ClimateMode::CLIMATE_MODE_HEAT:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_HEAT>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> HEAT [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    case climate::ClimateMode::CLIMATE_MODE_FAN_ONLY:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_FAN_ONLY>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> FAN [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    case climate::ClimateMode::CLIMATE_MODE_DRY:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_DRY>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> DRY [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    case climate::ClimateMode::CLIMATE_MODE_AUTO:
      this->request_OnOf->set_request('1');
      this->request_Mode->set_request(UintToString<Climate::CLIMATE_MODE_AUTO>::view());
      ESP_LOGV(TAG, "CONTROL: mode -> AUTO [%.*s]", this->request_Mode->view().size(), this->request_Mode->view().data());
      break;
    default:
      ESP_LOGW(TAG, "CONTROL: climate mode unsupported (%u)", *call.get_mode());;
  }
  
  switch ( call.get_fan_mode() ? *call.get_fan_mode() : *this->fan_mode ) {
    case climate::ClimateFanMode::CLIMATE_FAN_ON:
    case climate::ClimateFanMode::CLIMATE_FAN_AUTO:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_AUTO>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> AUTO [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    case climate::ClimateFanMode::CLIMATE_FAN_QUIET:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_QUIET>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> QUIET [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    case climate::ClimateFanMode::CLIMATE_FAN_LOW:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_LOW>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> LOW [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    case climate::ClimateFanMode::CLIMATE_FAN_MEDIUM:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_MEDIUM>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> MEDIUM [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    case climate::ClimateFanMode::CLIMATE_FAN_MIDDLE:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_MIDDLE>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> MIDDLE [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    case climate::ClimateFanMode::CLIMATE_FAN_HIGH:
      this->request_FanS->set_request(UintToString<Climate::CLIMATE_FAN_HIGH>::view());
      ESP_LOGV(TAG, "CONTROL: fan mode -> HIGH [%.*s]", this->request_FanS->view().size(), this->request_FanS->view().data());
      break;
    default:
      ESP_LOGW(TAG, "CONTROL: climate fan mode unsupported (%d)", *call.get_fan_mode());
  }
  
  switch ((call.get_swing_mode()) ? *call.get_swing_mode() : this->swing_mode) {
    case climate::ClimateSwingMode::CLIMATE_SWING_OFF:
      this->request_FanSw->set_request(UintToString<Climate::CLIMATE_SWING_OFF>::view());
      ESP_LOGV(TAG, "CONTROL: swing mode -> OFF [%.*s]", this->request_FanSw->view().size(), this->request_FanSw->view().data());
      break;
    case climate::ClimateSwingMode::CLIMATE_SWING_VERTICAL:
      this->request_FanSw->set_request(UintToString<Climate::CLIMATE_SWING_VERTICAL>::view());
      ESP_LOGV(TAG, "CONTROL: swing -> VERTICAL [%.*s]", this->request_FanSw->view().size(), this->request_FanSw->view().data());
      break;
    default:
      ESP_LOGW(TAG, "CONTROL: climate swing mode unsupported (%d)", *call.get_swing_mode());
  }
  

  if (call.has_custom_preset()) {
    if (call.get_custom_preset() == CLIMATE_CUSTOM_PRESET_SILENCE) {
        this->request_Opt1->set_request<uint8_t>(CLIMATE_PRESET_SILENCE >> 24 & 0xFF);
        this->request_Opt2->set_request<uint8_t>(CLIMATE_PRESET_SILENCE >> 16 & 0xFF);
        this->request_Opt3->set_request<uint8_t>(CLIMATE_PRESET_SILENCE >> 8 & 0xFF);
        this->request_Opt4->set_request<uint8_t>(CLIMATE_PRESET_SILENCE & 0xFF);
    }
  } else if (call.get_preset()) { 
    switch (*call.get_preset()) {
      case climate::CLIMATE_PRESET_AWAY:
        this->request_Opt1->set_request<uint8_t>(CLIMATE_PRESET_AWAY >> 24 & 0xFF);
        this->request_Opt2->set_request<uint8_t>(CLIMATE_PRESET_AWAY >> 16 & 0xFF);
        this->request_Opt3->set_request<uint8_t>(CLIMATE_PRESET_AWAY >> 8 & 0xFF);
        this->request_Opt4->set_request<uint8_t>(CLIMATE_PRESET_AWAY & 0xFF);
        break;
      case climate::CLIMATE_PRESET_BOOST:
        this->request_Opt1->set_request<uint8_t>(CLIMATE_PRESET_BOOST >> 24 & 0xFF);
        this->request_Opt2->set_request<uint8_t>(CLIMATE_PRESET_BOOST >> 16 & 0xFF);
        this->request_Opt3->set_request<uint8_t>(CLIMATE_PRESET_BOOST >> 8 & 0xFF);
        this->request_Opt4->set_request<uint8_t>(CLIMATE_PRESET_BOOST & 0xFF);
        break;
      case climate::CLIMATE_PRESET_ECO:
        this->request_Opt1->set_request<uint8_t>(CLIMATE_PRESET_ECO >> 24 & 0xFF);
        this->request_Opt2->set_request<uint8_t>(CLIMATE_PRESET_ECO >> 16 & 0xFF);
        this->request_Opt3->set_request<uint8_t>(CLIMATE_PRESET_ECO >> 8 & 0xFF);
        this->request_Opt4->set_request<uint8_t>(CLIMATE_PRESET_ECO & 0xFF);
        break;
      case climate::CLIMATE_PRESET_SLEEP:
        this->request_Opt1->set_request<uint8_t>(CLIMATE_PRESET_SLEEP >> 24 & 0xFF);
        this->request_Opt2->set_request<uint8_t>(CLIMATE_PRESET_SLEEP >> 16 & 0xFF);
        this->request_Opt3->set_request<uint8_t>(CLIMATE_PRESET_SLEEP >> 8 & 0xFF);
        this->request_Opt4->set_request<uint8_t>(CLIMATE_PRESET_SLEEP & 0xFF);
      case climate::CLIMATE_PRESET_NONE:
        break;
      default:
        ESP_LOGW(TAG, "CONTROL: preset unsupported (%d)", *call.get_preset());
      }
  } 
  if (!this->request_Opt1->has_request()) {
    this->request_Opt1->set_request<uint8_t>(0);
    this->request_Opt2->set_request<uint8_t>(0);
    this->request_Opt3->set_request<uint8_t>(0);
    this->request_Opt4->set_request<uint8_t>(0);
  }


  float target_temperature = (call.get_target_temperature()) ?  *call.get_target_temperature() : this->target_temperature;
  ESP_LOGV(TAG, "CONTROL: target temperature -> %.1f", target_temperature);
  this->request_SetT->set_request(target_temperature);

  this->get_parent()->schedule_message(this->control_);
}


climate::ClimateTraits Climate::traits() {
  this->traits_.set_supports_current_temperature(true);
  this->traits_.set_supports_current_humidity(true);
  return this->traits_;
}


void Climate::set_supported_modes(const std::set<climate::ClimateMode> &modes) {
  for (const auto mode : modes) {
    this->traits_.add_supported_mode(mode);
  }
  this->traits_.add_supported_mode(climate::CLIMATE_MODE_OFF);
}


void Climate::set_supported_swing_modes(const std::set<climate::ClimateSwingMode> &modes) {
  for (const auto mode : modes) {
    this->traits_.add_supported_swing_mode(mode);
  }
}


void Climate::set_supported_fan_modes(const std::set<climate::ClimateFanMode> &modes) {
  for (const auto mode : modes) {
    this->traits_.add_supported_fan_mode(mode);
  }
}


void Climate::set_supported_presets(const std::set<climate::ClimatePreset> &presets) {
  for (const auto preset : presets) {
    this->traits_.add_supported_preset(preset);
  }
}

void Climate::set_supported_custom_presets(const std::set<std::string> &presets) {
  this->custom_presets_storage_.assign(presets.begin(), presets.end());
  std::vector<const char *> preset_names;
  preset_names.reserve(this->custom_presets_storage_.size());
  for (const auto &preset : this->custom_presets_storage_) {
    preset_names.push_back(preset.c_str());
  }
  this->traits_.set_supported_custom_presets(preset_names);
} 


void Climate::set_supports_hvac_actions(bool support_hvac_actions) {
  this->traits_.set_supports_action(support_hvac_actions);
}


} // hlink2
} //esphome
