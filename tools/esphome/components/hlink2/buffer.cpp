
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <charconv>
#include <cstdlib>
#include <cstring>

#include "esphome/core/log.h"

#include "main.h"
#include "buffer.h"

namespace esphome {
namespace hlink2 {
static const char *const TAG = "hlink2:buffer";

/*---- GENERIC BUFFER OPERATIONS ----*/ 

void IOBuffer::set_state(const IOBuffer::State &state, size_t header_size) {
    switch (state) {
      case IOBuffer::State::EMPTY:
        this->size_ = header_size;
        this->view = std::string_view(this->data_.data(), header_size);
        break;
      case IOBuffer::State::READY:
        this->view = std::string_view(this->data_.data(), this->size_);
      default:
        break;
    }
    this->state_ = state;
  }


/*---- WRITE BUFFER OPERATIONS ----*/ 
void IOBuffer::append(char c) { 
  if (!this->free()) {
    ESP_LOGE(TAG, "buffer overflow");
    this->state_ = State::INVALID;
    return;
  }
  this->data_[this->size_++] = c;
}


void IOBuffer::append(std::string_view data) {
  if (data.size() > this->free()) {
    ESP_LOGE(TAG, "Buffer overflow");
    this->state_ = IOBuffer::State::INVALID;
    return;
  }
  memcpy(this->next(), data.data(), data.size());
  this->size_ += data.size();
}


void IOBuffer::append_request(uint8_t order, const char* value) {
  this->append("\"D%u\":\"", order);
  this->append(value);
  this->append("\",");
  ESP_LOGVV(TAG, "FORMAT: mnemonic %s done", mnemonic->name);
}

void IOBuffer::append_request(const char* key, std::string_view value) {
    this->append('"');
    this->append(key);
    this->append("\":");
    this->append(value);
    this->append(',');
}

/*---- READ BUFFER OPERATIONS ----*/ 

void IOBuffer::update() {
  switch (this->state_) {
    case State::EMPTY:
    case State::INVALID:
      for (size_t pos = 0; pos < this->size(); pos++) {
        if (this->data_[pos] == MESSAGE_BOUNDARIES.start) {
          ESP_LOGVV(TAG, "START boundary found (char %d)", pos);
          size_t new_size = this->size() - pos;
          memmove(this->data_.data(), this->data_.data() + pos, new_size);
          this->view = std::string_view(this->data_.data(), new_size); 
          this->set_size(new_size);
          this->state_ = State::PARTIAL;  // set_state not used here to skip the internal switch
          break;
        }
      }
      if (this->state_ != State::PARTIAL) break;
      // fallthrough if (state_ == State::PARTIAL) to check end boundary
    case State::PARTIAL:
      for (size_t pos = this->size(); pos > MESSAGE_SIZE_MIN ;) {
        if (this->data_[--pos] == MESSAGE_BOUNDARIES.end) {
          if (this->data_[pos-1] != '}') {
            ESP_LOGE(TAG, "invalid end chars (pos %d) [0x%02X 0x%02X]", pos, this->data_[pos-1], this->data_[pos]);
                        this->state_ = State::INVALID;
            return;
          }
          size_t new_size = pos + 1;
          this->view = std::string_view(this->data_.data(), new_size); 
          this->set_size(new_size);
          this->state_ = State::READY; // set_state not used here to skip the internal switch
          return;
        }
      }
      this->view = std::string_view(this->data_.data(), this->size());
      break;
    case State::READY:
      this->view = std::string_view(this->data_.data(), this->size());
      break;
    default:
      break;
  }
}
 

bool IOBuffer::extract_int(const char* key, uint16_t &value) {
  size_t pos = this->view.find(key);
  if (pos == std::string_view::npos) {
    ESP_LOGE(TAG, "extract_int: missing '%s' mnemonic", key);
    return false;
  }
  size_t key_len = std::strlen(key);
    if (pos + key_len >= this->view.size()) {
        ESP_LOGE(TAG, "extract_int: insufficient data after '%s'", key);
        return false;
  }
  this->view.remove_prefix(pos + key_len);

  auto result = std::from_chars(this->view.data(), this->view.data() + this->view.size(), value);
  if (result.ec != std::errc()) {
    ESP_LOGE(TAG, "extract_int: invalid '%s' value", key);
    return false;
  }
  this->view.remove_prefix(result.ptr - this->view.data());
  return true;
}


bool IOBuffer::extract_key(std::string_view &key, uint8_t max_bytes) {
  size_t start;
  size_t view_size = this->view.size();
  for (start = 0; start < view_size;) { /// TODO: limit search to N chars
    if (this->view[start++] == '"') {
      break;
    }
  }

  if (start == view_size) {
      ESP_LOGE(TAG, "extract_key: no key found");
      return false;
  }
  size_t boundary = std::min<size_t>(max_bytes + start, view_size - start - 1);
  for (size_t end = start; end < boundary; ++end) {
    if (this->view[end] == '"' && this->view[end+1] == ':') {
      key = this->view.substr(start, end - start);
      this->view.remove_prefix(end + 2); // remove the trailing '":'
      ESP_LOGVV(TAG, "PARSE: found key %.*s", key.size(), key.data());
      return true;
    }
  }
  ESP_LOGE(TAG, "extract_key: no key in %.*s", boundary, view.data());
  return false;
}


bool IOBuffer::extract_value(std::string_view &value, uint8_t max_bytes) {
  size_t boundary = std::min<size_t>(max_bytes, this->view.size());
  uint8_t len = 0;
  while (len < boundary && this->view[len] != ',' && this->view[len] != '}') {
    ++len;
  }
  if (len == 0) {
    ESP_LOGE(TAG, "extract_value: underflow");
    return false;
  }

  if (len == boundary) {
    ESP_LOGE(TAG, "extract_value: overflow");
    return false;
  }

  value = this->view.substr(0, len);
  this->view.remove_prefix(len);
  return true;
}

} // hlink2
} //esphome