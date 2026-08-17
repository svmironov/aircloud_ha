#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string_view>

#include "esphome/core/log.h"
#include "main.h"


namespace esphome {
namespace hlink2 {

struct IOBuffer {
  enum class State: uint8_t {
    EMPTY,
    PARTIAL,
    READY,
    INVALID
  };

  std::array<char, MESSAGE_BUFFER_SIZE> data_{};  // buffer
  std::string_view view{data_.data(), 0}; // inner operations
  size_t size_{0};
  State state_{State::EMPTY};
  size_t cursor_{0};

  IOBuffer(){};
  IOBuffer(const char* data){this->append(data);};

  /*---- COMMON BUFFER OPERATIONS ----*/ 
  inline State state() {return this->state_;};
  inline char& operator[](size_t index) {return this->data_[index];};

  // size
  inline size_t size() const {return this->size_;};
  inline void set_size(size_t size) {this->size_ = size;};
  void set_state(const State &state, size_t header_size=0);

  // partial buffer

  /// update buffer (state, view)
  void update();

  // return current index of view in data
  inline size_t view_index() { return static_cast<size_t>(this->view.data() - this->data_.data()); }

  /// reset view to data size
  inline void reset_view() { this->view = std::string_view(this->data_.data(), this->size_); }

  //extending buffer
  inline size_t free() { return this->data_.size() - this->size_; } // remaining free space

  // next data slot after current size
  inline char* next() { return this->data_.data() + this->size_; }

  /*---- WRITE BUFFER OPERATIONS ----*/ 
  void append(char c);
  void append(std::string_view data);
  inline void append(const char* data) {if (data) append(std::string_view(data));}

  /// append a request "Dorder":"value"
  void append_request(uint8_t order, const char*);

  /// append a request "key":"value"
  void append_request(const char*, std::string_view);

  /// append a pattern filled with args, updating state accordingly
  template<typename... VariadicArgs>
  void append(const char* pattern, VariadicArgs&&... args) {
    size_t remaining = this->free();
    int len = std::snprintf(this->next(), remaining, pattern, std::forward<VariadicArgs>(args)...);
    if (len < 0) {
      ESP_LOGE("hlink2:buffer", "Buffer error: failed to write (pattern %s)", pattern);
      this->state_ = IOBuffer::State::INVALID;
      return;
    } else if (static_cast<size_t>(len) >= remaining) {
      ESP_LOGE("hlink2:buffer", "Buffer error: overflow (pattern: %s)", pattern);
      this->state_ = IOBuffer::State::INVALID;
      return;
    }
    this->size_ += static_cast<size_t>(len);
  }

  /*---- READ BUFFER OPERATIONS ----*/
  /// given a key, find an int value and move view after it
  bool extract_int(const char* key, uint16_t &value);

  /// find a key (length limited to max_bytes) and move view after it
  bool extract_key(std::string_view &key, uint8_t max_bytes=MESSAGE_BUFFER_KEY_SIZE.max);

  /// find a value right after a key and move view after it
  bool extract_value(std::string_view &value, uint8_t max_bytes=MESSAGE_BUFFER_VALUE_SIZE.max);
};

} // hlink2
} //esphome
