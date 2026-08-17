#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <utility>

#include "esphome/core/hal.h"
#include "esphome/core/helpers.h"


namespace esphome {
namespace hlink2 {


#define ENUM_CAST(value) static_cast<std::underlying_type_t<decltype(value)>>(value)

/// DJB2A hash of a string for fast comparaison of mnemonics
/// hash collisions tests are handled by python code
constexpr uint32_t hasher(std::string_view data, uint32_t hash = 5381) {
    for (unsigned char c : data) {
      hash = ((hash << 5) + hash) ^ c;
    }
    return hash;
}


struct Timer {
  public:
    Timer(){};
    Timer(uint32_t delay) {this->set(delay);} ;

    inline uint32_t expiration() {return this->value_;}
    inline void set(uint32_t delay) {this->value_ = millis() + delay;}
    inline bool expired() const {return (int32_t)(millis() - this->value_) >= 0;}
  
  protected:
    uint32_t value_;
};


/// Timer carrying a delay value. Never expire if dekay is zero
struct CyclicTimer: Timer {
  public:
    CyclicTimer(){};
    CyclicTimer(uint32_t delay) {this->set(delay);}
    
    /// update status timeout delay if delay is shorter. zero means no timeout.
    void set(uint32_t delay) {
      if (delay == 0 || this->delay_ == 0 || delay < this->delay_) {
        this->delay_ = delay;
      }
      Timer::set(this->delay_);
    }

    /// restart timer
    inline void restart() {Timer::set(this->delay_);}

    /// return whether timer has expired
    inline bool  expired() const {return this->delay_ && Timer::expired();};
    
    ///return timer fixed delay before expiration
    inline uint32_t delay() const {return  this->delay_;}
    
    /// force timer expiration
    inline void force_expiration() { this->value_ = 0; }
  
  protected:
     uint32_t delay_{0}; 
};


/// Callback functions handler
struct CallbacksHandler {
  /// add a new status callback
  template<typename FUNC>
  void add_callback(FUNC&& func) {
    callbacks.add(std::forward<FUNC>(func));
  }

  /// run the status callbacks
  void run_callbacks() {
    callbacks();
  };
  
  protected:
    CallbackManager<void()> callbacks;
};


/// char buffer
template<size_t SIZE, bool NULL_TERMINATED = false>
struct CharBuffer {
  static_assert(SIZE > (1 + static_cast<int>(NULL_TERMINATED)), "SIZE too small");

  protected:
    std::array<char, SIZE> data_{};
    size_t size_{0};
    static constexpr size_t capacity_ = NULL_TERMINATED ? SIZE -1 : SIZE;
    
  public:
    static constexpr size_t npos = size_t(-1);

    CharBuffer() {
      if constexpr (NULL_TERMINATED) {
        data_[0] = '\0';
        data_[capacity_] = '\0'; // prevent overflow
      }
    }
    
    inline const char* data() const noexcept { return data_.data(); }
    inline char* data() noexcept { return data_.data(); }
    inline size_t size() const noexcept { return size_; }
    inline size_t capacity() const noexcept { return capacity_; }
    inline bool empty() const noexcept { return size_ == 0; }
    inline const char* begin() const noexcept { return data_.begin(); }
    inline const char* end() const noexcept { return data_.begin() + size_; }
    inline const char& front() const noexcept { return data_.front(); }
    inline const char& back() const noexcept { return empty() ? data_.front() : data_[size_ - 1]; }
    inline const char& operator[](size_t pos) const noexcept { return data_[pos < size_ ? pos : 0]; }

    inline operator std::string_view() const noexcept { return {data_.data(), size_}; }
    inline std::string_view view() const noexcept { return {data_.data(), size_}; }
    std::string_view substr (size_t pos = 0, size_t n = npos) const noexcept {
      if (pos >= size_) return {nullptr, 0};
      size_t len = (n == npos || pos + n > size_) ? size_ - pos : n;
      return {data_.data() + pos, len};
    }

    inline const char* c_str() const noexcept {
      if constexpr (NULL_TERMINATED)  return data_.data();
      static_assert(NULL_TERMINATED, "c_str() requires NULL_TERMINATED = true");
    }

    /// set the view, truncating if exceeding capacity (en returning false then)
    bool set(std::string_view sv) noexcept {
      size_ = (sv.size() > capacity_) ? capacity_: sv.size();
      //char buff[this->capacity_];
      //std::memcpy(buff, sv.data(), size_);
      //std::memcpy(data_.data(), buff, size_);
      std::memcpy(data_.data(), sv.data(), size_);
      if constexpr (NULL_TERMINATED) data_[size_] = '\0';
      return size_ == sv.size();
    }

    /// set first byte
    void set(char c) noexcept {
      data_[0] = c;
      size_ = 1;
      if constexpr (NULL_TERMINATED) data_[1] = '\0';
    }

    /// add string_view at the end of view, truncating if exceeding capacity (and returning false then)
    bool append(std::string_view sv) noexcept {
      size_t len = (sv.size() + size_ > capacity_) ? capacity_ - size_ : sv.size();
      std::memcpy(data_.data() + size_, sv.data(), len);
      size_ += len;
      if constexpr (NULL_TERMINATED) data_[size_] = '\0';
      return len == sv.size();
    }

    /// append char at the end of the view if possible
    bool append(char c) noexcept {
      if (size_ == capacity_) return false;
      data_[size_++] = c;
      if constexpr (NULL_TERMINATED) data_[size_] = '\0';
      return true;
    }

    inline void clear() noexcept { this->size_ = 0;}
    void resize(size_t s) noexcept {
      size_ = (s > capacity_) ? capacity_ : s;
      if constexpr (NULL_TERMINATED) data_[size_] = '\0';
    }
};


/// Ring vector implementation
template<typename TYPE, size_t SIZE>
struct RingVector {
  public:
    bool push_back(TYPE data) {
      if (size_ >= SIZE) return false;
      tail_ = wrap(tail_ + 1);
      ring[tail_] = std::move(data);
      size_++;
      return true;
    }

    template<typename... Args>
    bool emplace_front(Args&&... args) {
      if (size_ >= SIZE) return false;
      head_ = (head_ == 0 ? SIZE - 1 : head_ - 1);
      ring[head_] =  TYPE(std::forward<Args>(args)...);
      size_++;
      return true;
    }

    template<typename... Args>
    bool emplace_back(Args&&... args) {
      if (size_ >= SIZE) return false;
      tail_ = wrap(tail_ + 1);
      ring[tail_] =  TYPE(std::forward<Args>(args)...);
      size_++;
      return true;
    }

    bool pop_front() {
      if (size_ == 0) return false;
      head_ = wrap(head_ + 1);
      size_--;
      return true;
    }

    bool pop_back() {
      if (size_ == 0) return false;
      tail_ = wrap(tail_ + SIZE - 1);
      size_--;
      return true;
    }

    /// put the first item to the last place
    bool rotate() {
      if (size_ == 0) return false;
      tail_ = wrap(tail_ + 1);
      std::swap(ring[tail_],ring[head_]);
      head_ = wrap(head_ + 1);
      return true;
    }

    void clear() {
      size_ = 0;
      head_ = 0;
      tail_ = SIZE-1;
    }

    inline bool empty() {return size_ == 0;}
    inline bool full() {return size_ == SIZE;}

    inline TYPE& operator[](size_t index) {return ring[wrap(index + head_)];}
    inline TYPE& front() {return (ring[head_]);} 
    inline TYPE& back() {return ring[tail_];}
    inline size_t size() const {return size_;}
    static inline constexpr size_t capacity() {return SIZE;}

    void copy(const RingVector& other) noexcept(std::is_trivially_copyable_v<TYPE>) {
      std::copy(other.ring.begin(), other.ring.end(), ring.begin());
      head_ = other.head_;
      tail_ = other.tail_;
      size_ = other.size_;
    }
  
  protected:
    std::array<TYPE, SIZE> ring{};
    size_t head_{0};
    size_t tail_{SIZE-1};
    size_t size_{0};
  
  private:
    /// faster modulo method (equivalent to value % SIZE)
    inline size_t wrap(size_t index) {
      return index >= SIZE ?  index - SIZE: index;
    }
};

/// Ordered vector of pointers: pending items always first, then selected items
template<typename TYPE, size_t SIZE>
struct OrderedVector {
private:
  using Vector = RingVector<TYPE, SIZE>;
  Vector queue1{};
  Vector queue2{};
  Vector* pending = &queue1;
  Vector* selected = &queue2;

  size_t size_{0};

public:
  enum CHOICE: int8_t {
    PASS = 0,
    SELECT = 1,
    REMOVE = -1
  };

  inline size_t size() const {return this->size_;};

  TYPE* operator[](size_t index) const {
    if (index < this->pending->size()) {
      return this->pending[index];
    } else {
      return this->selected[index - this->selected->size()];
    }
  }

  bool add(TYPE item) {
    if (size_ == SIZE) {
      return false;
    }

    // for (size_t i=0; i < pending->size(); i++) {
    //   if (item == (*pending)[i]) {
    //     return true;  // avoid redundancy 
    //   }
    // }
    // for (size_t i=0; i < selected->size(); i++) {
    //   if (item == (*selected)[i]) {
    //     return true;  // avoid redundancy 
    //   }
    // }
    
    this->pending->push_back(item);
    ++this->size_;
    return true;
  }


  /// pop back item from either pending or selected
  bool pop_back(TYPE item) {
    if (this->pending->back() == item && this->pending->pop_back()) {
      --this->size_;
      return true;
    }
    if (this->selected->back() == item && this->selected->pop_back()) {
      --this->size_;
      return true;
    }
    return false;
  }
  
  // reorder the vector according to a func which must return 1 (select), 0 (pass) or -1 (remove)
  template<typename SELECT_FUNC>
  TYPE select(SELECT_FUNC&& func) {
    size_t pending_size = this->pending->size();
    size_t selected_size = this->selected->size();
    TYPE item{nullptr};

    for (size_t count = 0; count < pending_size; count++) {
      switch (func(this->pending->front())) {
        case SELECT:
          item = this->pending->front();
          this->selected->push_back(item);
          this->pending->pop_front();

          if (this->pending->size() == 0) {
            std::swap(this->pending, this->selected);
          }
          return item;
        case REMOVE:
          this->pending->pop_front();
          --this->size_;
          break;
        default:
          this->pending->rotate();
      }
    }
    for (size_t count = 0 ; count < selected_size; count++) {
      switch (func(this->selected->front())) {
        case SELECT:
          item = this->selected->front();
          this->selected->rotate();
          return item;
        case REMOVE:
          this->selected->pop_front();
          --this->size_;
          break;
        default:
          this->pending->push_back(this->selected->front());
          this->selected->pop_front();
      }
    }
    if (this->pending->size() == 0) {
      std::swap(this->pending, this->selected);
    }
    return nullptr;
  }
};


template<uint16_t N>
struct UintToString {
  private:
    static constexpr std::array<char,7> buffer = [] {
      std::array<char,7> b = {};
      uint8_t pos = 6; // last position is \x00
      uint16_t t = N;
      
      do {
        b[--pos] = '0' + (t % 10);
        t /= 10;
      } while (t > 0 && pos > 1);
      b[0] = 6 - pos;
      return b;
    }();
  public:
    inline static constexpr std::size_t size() noexcept { return buffer[0]; }
    inline static constexpr const char* c_str() noexcept { return &buffer[6-size()];};
    inline static constexpr std::string_view view() noexcept {
      return {&buffer[6 - size()], size()};
    }
};


/// fast modulo calculation (provided value is not too far from MODULO)
template<typename TYPE, TYPE MODULO>
inline TYPE modulo(TYPE value) {
  while (value >= MODULO) {
    value -= MODULO;
  }
  return value;
}

/// return a string where invisibles chars are replaced by hex
inline std::string debug_data(const uint8_t* data, size_t len) {
  static const char hex[] = "0123456789ABCDEF";
  std::string result;
  result.reserve(len * 3 + 1);

  for (size_t i = 0; i < len; ++i) {
    if (data[i] < 32 || data[i] > 126) {
      result += '|';
      result += hex[data[i] >> 4];
      result += hex[data[i] & 0xF];
    } else {
        result += static_cast<char>(data[i]);
    }
  }
  return result;
}


} // hlink2
} //esphome
