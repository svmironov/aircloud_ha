#include <cstddef>
#include <cstdint>
#include <string_view>

#include "esphome/core/log.h"

#include "message.h"
#include "buffer.h"
#include "main.h"
#include "tools.h"
#include "mnemonics.h"

namespace esphome {
namespace hlink2 {

static const char *const TAG = "hlink2:message";

Request* Message::add(Mnemonic& m) {
  if (!m.match_mode(this->flag->mode)) {
    ESP_LOGE(TAG, "@%p: adding mnemonic %s: unsupported mode", this, m.name);
    return nullptr;
  }
  if (Request* request = this->get_request(m)) {
    ESP_LOGW(TAG, "@%p: adding mnemnonic %s: already present", this, m.name);
    return request;
  }
  ESP_LOGD(TAG, "@%p: adding mnemonic %zu: %s", this, this->size()+1, m.name);
  if (this->requests_.emplace_back(m)) {
    return &this->requests_.back();
  }
  return nullptr;
}


bool Message::has(Mnemonic& m) {
  for (size_t i=0; i< this->requests_.size(); i++) {
    if (this->requests_[i].mnemonic() == &m) {
      return true;
    }
  }
  return false;
}

Request* Message::get_request(Mnemonic& m) {
  for (size_t i=0; i<this->requests_.size(); ++i) {
    if (this->requests_[i].mnemonic() == &m) {
      return &this->requests_[i];
    }
  }
  return nullptr;
}


Request* Message::get_request(size_t index) {
  if (index < this->requests_.size()) {
    return &this->requests_[index];
  }
  return nullptr;
}

bool Message::has_requests() {
  for (size_t i = 0; i < this->requests_.size(); i++) {
    if (this->requests_[i].has_request()) return true;
  }
  return false;
}


void Message::clear_requests() {
  for (size_t i = 0; i < this->requests_.size(); i++) {
    this->requests_[i].clear_request();
  }
  ESP_LOGV(TAG, "@%p: commands cleared", this);
}


void Message::apply_requests() {
  this->response_mnemonics.clear();
  for (size_t i = 0; i < this->requests_.size(); i++) {
    this->requests_[i].apply_request();
    this->response_mnemonics.push_back(this->requests_[i].mnemonic());
  }
  ESP_LOGV(TAG, "@%p: pending applied", this);
}


Message::State Message::state() {
  switch (this->state_.value) {
    case State::INITIALIZED:
    case State::PARSED:
    case State::PROCESSED:
    case State::EXPIRED:
    case State::INVALID:
      break;
    case State::SCHEDULED:
    case State::FORMATTED:
    case State::SENT:
    case State::RECEIVED:
      if (
        this->transaction_started_
        && (!this->state_.attempts || this->state_.timer.expired())
      ) {
        ESP_LOGV(TAG, "@%p : EXPIRED", this);
        this->state_.value = Message::State::EXPIRED;
      }
  }
  return this->state_.value;
}


Message::State Message::set_state(const Message::State &state) {
  /* set message state update internals accordingly */
  if (state == Message::State::INVALID) { // return to previous state if allowed, otherwise EXPIRED
    ESP_LOGV(TAG, "@%p: INVALID", this);
    // INVALID can also be used to discard an unscheduled custom message. In
    // that case attempts is still zero; decrementing it used to wrap uint8_t to
    // 255 and left the ephemeral slot permanently stuck in INITIALIZED.
    if (!this->state_.attempts) {
      this->state_.value = Message::State::EXPIRED;
      return this->state_.value;
    }
    this->state_.attempts--;
    return this->state() == State::EXPIRED ? State::EXPIRED : this->state_.value;
  }
  ESP_LOGV(TAG, "%p: %s", this, Message::StateName[static_cast<uint8_t>(state)]);
  this->state_.value = state;
  return state;
}


void Message::initialize() {
  if (this->flag->mode == Mnemonic::Mode::CMD) { // STS message request buffer is immutable
    this->request_buffer_.set_state(IOBuffer::State::EMPTY, MESSAGE_HEAD_SIZE);
  }
  
  this->request_buffer_.reset_view();
  this->response_mnemonics.clear();
  this->response.reset();
  this->transaction_started_ = false;
  this->set_state(Message::State::INITIALIZED);
}


void Message::initialize(uint32_t delay) {
  if (delay) this->state_.timer.set(delay);
  this->initialize();
}


void Message::schedule() {
  this->state_.attempts = static_cast<uint8_t>(this->qos);
  this->transaction_started_ = false;
  ESP_LOGV(TAG, "@%p: %d attempts; timeout starts when selected for the bus", this, this->state_.attempts);
  switch (this->request_buffer_.state()) {
    case IOBuffer::State::READY:
      this->set_state(Message::State::FORMATTED);
      return;
    default:
      this->set_state(Message::State::SCHEDULED);
  }
}


Message::State Message::format() {
  switch (request_buffer_.state()) {
    case IOBuffer::State::READY:
      ESP_LOGW(TAG, "Message format: buffer already READY");
      return this->set_state(Message::State::FORMATTED);
    case IOBuffer::State::EMPTY:
      break;
    case IOBuffer::State::PARTIAL: //not handled yet
    case IOBuffer::State::INVALID:
      request_buffer_.set_state(IOBuffer::State::EMPTY);
      break;
  }

  if (!this->size()) {
    ESP_LOGW(TAG, "Message format: no mnemonics to format");
    return this->set_state(Message::State::INVALID);
  }

  //add DataN
  size_t DataN = this->requests_.size();

  /// TODO: find a better way to update DataN according to commands states
  if (this->flag->mode == Mnemonic::Mode::CMD) {
    for (size_t i=0; i<this->requests_.size(); ++i) {
      if (!this->requests_[i].has_request()) --DataN;
    }
  }
  request_buffer_.append("%d}", DataN);
  
  // add flag
  size_t value_start = request_buffer_.size(); // store current size to compute checksum later
  request_buffer_.append("{\"%s\":{", this->flag->raw);

  if (request_buffer_.state() == IOBuffer::State::INVALID) {
    ESP_LOGE(TAG, "Message format: header write failed");
    return this->set_state(Message::State::INVALID);
  }
  
  // add mnemonics
  ESP_LOGVV(TAG, "FORMAT: %d mnemonics to format", this->requests_.size());
  for (size_t i = 0; i < this->requests_.size(); i++) {
    Mnemonic* mnemonic = this->requests_[i].mnemonic();
    ESP_LOGVV(TAG, "mnemonic %s (%lu/%lu)", mnemonic->name, i+1, this->requests_.size(), mnemonic);

    if (this->flag->mode == Mnemonic::Mode::CMD) {
      if (this->requests_[i].has_request()) { 
        request_buffer_.append_request(mnemonic->name, this->requests_[i].view());
      } else {
        ESP_LOGW(TAG, "FORMAT: mnemonic %s: skipped, no value", mnemonic->name);
        continue;
      }
    } else {
      request_buffer_.append_request(i+1, mnemonic->name);
      ESP_LOGVV(TAG, "FORMAT: mnemonic %s done", mnemonic->name);
    }
    
    if (request_buffer_.state() == IOBuffer::State::INVALID) {
      ESP_LOGE(TAG, "Message format: failed to write mnemonic %s", mnemonic->name);
      return this->set_state(Message::State::INVALID);
    }
  }

  if (this->requests_.size() > 0) {
    // replace last ',' by '}}'
    if (request_buffer_.free() < 2) {
      ESP_LOGE(TAG, "Message format: unable to set value last bytes");
      request_buffer_.set_state(IOBuffer::State::EMPTY);
      return this->set_state(Message::State::INVALID);
    }
    request_buffer_[request_buffer_.size()-1] = '}';
    request_buffer_.append('}');
  }

  // add checksum
  uint16_t checksum = 0xFFFF;
  for (size_t i = value_start; i < request_buffer_.size(); i++) {
    checksum -= static_cast<uint8_t>(request_buffer_[i]);
  }
  request_buffer_.append("{\"ChS\":%d}}\x03", checksum);

  if (request_buffer_.state() != IOBuffer::State::INVALID) {
    request_buffer_.set_state(IOBuffer::State::READY);
    return this->set_state(Message::State::FORMATTED);
  } else {
    request_buffer_.set_state(IOBuffer::State::EMPTY);
    return this->set_state(Message::State::INVALID);
  }
}


Message::State Message::parse(IOBuffer &buffer) {
  /* parse a buffer to update a message */
  if (buffer.state() != IOBuffer::State::READY) {
    ESP_LOGE(TAG, "PARSE: buffer not ready (%d)", static_cast<uint8_t>(buffer.state()));
    return this->set_state(Message::State::INVALID);
  }

  // A checksum/framing failure can retry the same Message object. Do not keep
  // mnemonics or a response value collected by the failed parse; otherwise the
  // fixed-capacity queue fills with duplicates and every later retry fails too.
  this->response_mnemonics.clear();
  this->response.reset();

  // check boundaries
  if (buffer.view[0] != MESSAGE_BOUNDARIES.start || buffer.view[buffer.size()-1] != MESSAGE_BOUNDARIES.end) {
    ESP_LOGE(TAG, "PARSE: missing message boundaries");
    return this->set_state(Message::State::INVALID);
  }

  // parse Mnemonic count (DataN)
  uint16_t DataN = 0;
  if (!buffer.extract_int("DataN\":", DataN)) {
    ESP_LOGE(TAG, "PARSE: 'DataN' mnemonic not found");
    return this->set_state(Message::State::INVALID);
  }

  if (DataN == 0) { //stop parsing if message payload is empty (invalid or)
    ESP_LOGE(TAG, "PARSE: empty payload");
    return this->set_state(Message::State::INVALID);
  }
  ESP_LOGVV(TAG, "PARSE: 'DataN' is %d", DataN);
  const char* checksum_start = buffer.view.data() + 1;
  const char* checksum_end = nullptr;

  // parse response (Res)
  uint16_t response;
  if (!buffer.extract_int("Res\":", response)) {
    ESP_LOGE(TAG, "PARSE: 'Res' mnemonic not found");
    return this->set_state(Message::State::INVALID);
  }
  this->response = static_cast<Message::Response>(response);
  ESP_LOGVV(TAG, "PARSE: Response is %d", response); 

  // parse message flag
  std::string_view key;
  if(!buffer.extract_key(key, MESSAGE_BUFFER_KEY_SIZE.max)) {
    ESP_LOGE(TAG, "no message Flag found");
    return this->set_state(Message::State::INVALID);
  }
  uint32_t key_hash = hasher(key);
  const Message::Flag* flag = Message::Flag::from_hash(key_hash);
  if (flag == &Message::Flag::None) {
    if (key_hash == hasher("ChS")) { // reached end of message
      checksum_end = key.data()-2;
    } else {
      ESP_LOGE(TAG, "no valid Flag found: %.*s", key.size(), key.data());
      return this->set_state(Message::State::INVALID);
    }
  } else {
    ESP_LOGVV(TAG, "PARSE: Flag is %s", flag->raw);
  }
  

  // extract mnemonics
  for (uint8_t i = 1; i < DataN; i++){

    if (buffer.view.size() < MESSAGE_BUFFER_ITEM_SIZE.min) {
      ESP_LOGE(TAG, "PARSE: failed to extract memonic, buffer underflow");
      return this->set_state(Message::State::INVALID);
    }
    
    // extract mnemonic key
    std::string_view key;
    if (!buffer.extract_key(key, MESSAGE_BUFFER_KEY_SIZE.max)) {
      ESP_LOGE(TAG, "no mnemonic key found in %u bytes", MESSAGE_BUFFER_KEY_SIZE.max);
      return this->set_state(Message::State::INVALID);
    }
    Mnemonic* mnemonic = Mnemonic::from_hash(hasher(key, static_cast<uint32_t>(flag->dest)));
    ESP_LOGVV(TAG, "PARSE: mnemonic %zu is %s", i, mnemonic->name);

    //extract mnemonic value
    std::string_view value;
    if (!buffer.extract_value(value, MESSAGE_BUFFER_VALUE_SIZE.max)) {
      ESP_LOGE(TAG, "PARSE: mnemonic %s: no value found in %zu bytes", mnemonic->name, MESSAGE_BUFFER_VALUE_SIZE.max);
      return this->set_state(Message::State::INVALID);
    }
    mnemonic->set_status(value);
    ESP_LOGVV(TAG, "PARSE: mnemonic %s: value is %.*s", mnemonic->name, mnemonic->status().size(), mnemonic->status().data());

    if (!this->response_mnemonics.push_back(mnemonic)) {
      ESP_LOGE(TAG, "PARSE: response mnemonic queue full");
      return this->set_state(Message::State::INVALID);
    }
  }

  if (checksum_end == nullptr) {
    std::string_view key;
    if(!buffer.extract_key(key, MESSAGE_BUFFER_KEY_SIZE.max) || key != "ChS") {
      ESP_LOGE(TAG, "no valid checksum key found");
      return this->set_state(Message::State::INVALID);
    }
    checksum_end = key.data()-2;
  }

  size_t count = checksum_end - checksum_start;
  uint16_t checksum_calc = 0xFFFF;
  uint16_t checksum_read;
  
  for (size_t i = 0; i < count; ++i) {
    checksum_calc -= static_cast<uint8_t>(*(checksum_start+i));
  }

  auto result = std::from_chars(buffer.view.data(), buffer.next(), checksum_read);
  if (result.ec != std::errc()) {
    ESP_LOGE(TAG, "PARSE: invalid checksum");
    return this->set_state(Message::State::INVALID);
  }

  if (checksum_calc != checksum_read) {
    ESP_LOGE(TAG, "PARSE: bad checksum (calc=%u|read=%u)", checksum_calc, checksum_read);
    return this->set_state(Message::State::INVALID);
  }
  buffer.set_state(IOBuffer::State::EMPTY);
  return this->set_state(Message::State::PARSED);
}


} // hlink2
} //esphome
