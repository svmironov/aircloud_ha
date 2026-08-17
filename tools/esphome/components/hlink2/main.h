#pragma once

#include <cstddef>
#include <cstdint>

#include "esphome/core/defines.h" // location of custom definitions

namespace esphome {
namespace hlink2 {

#define DEBUG_HLINK2

#ifndef CONF_MESSAGE_PERSISTENT_VECTOR_SIZE
  #define CONF_MESSAGE_PERSISTENT_VECTOR_SIZE 30
#endif

#ifndef CONF_MESSAGE_EPHEMERAL_VECTOR_SIZE
  #define CONF_MESSAGE_EPHEMERAL_VECTOR_SIZE 10
#endif

#ifndef CONF_MESSAGE_RECEIVED_VECTOR_SIZE
  #define CONF_MESSAGE_RECEIVED_VECTOR_SIZE 10
#endif

#ifndef CONF_UART_TX_CHUNK_SIZE
  #define CONF_UART_TX_CHUNK_SIZE 16
#endif
#ifndef CONF_MESSAGE_MNEMONICS_CAPACITY
  #define CONF_MESSAGE_MNEMONICS_CAPACITY 13
#endif
#ifndef CONF_TASK_TIMEOUT
  #define CONF_TASK_TIMEOUT 30
#endif
#ifndef CONF_MESSAGE_UPDATE_INTERVAL
  #define CONF_MESSAGE_UPDATE_INTERVAL 60000
#endif
#ifndef CONF_MESSAGE_UPDATE_TIMEOUT
  #define CONF_MESSAGE_UPDATE_TIMEOUT 2500
#endif
#ifndef CONF_MESSAGE_BUZZER
  #define CONF_MESSAGE_BUZZER true
#endif
#ifndef CONF_MESSAGE_STS_PROMOTE
  #define CONF_MESSAGE_STS_PROMOTE true
#endif
#ifndef CONF_MESSAGE_STS_QOS
  #define CONF_MESSAGE_STS_QOS Message::QoS::QOS_LOW //1 // 1 = LOW
#endif
#ifndef CONF_MESSAGE_CMD_QOS
  #define CONF_MESSAGE_CMD_QOS Message::QoS::QOS_HIGH //3 // 3 = HIGH
#endif
#ifndef CONF_MESSAGE_CMD_RAW
  #define CONF_MESSAGE_CMD_RAW false
#endif


#ifdef USE_CLIMATE
class Climate;
#endif
#ifdef USE_SENSOR
class Sensor;
#endif
#ifdef USE_SWITCH
class Switch;
#endif
#ifdef USE_TEXT_SENSOR
class TextSensor;
#endif
#ifdef USE_NUMBER
class Number;
#endif

#define USE_API
  constexpr const size_t MESSAGE_PERSISTENT_VECTOR_SIZE = CONF_MESSAGE_PERSISTENT_VECTOR_SIZE;
  constexpr const size_t MESSAGE_EPHEMERAL_VECTOR_SIZE = CONF_MESSAGE_EPHEMERAL_VECTOR_SIZE;
  constexpr const size_t MESSAGE_RECEIVED_VECTOR_SIZE = CONF_MESSAGE_RECEIVED_VECTOR_SIZE;

  constexpr const uint8_t TASK_TIMEOUT = CONF_TASK_TIMEOUT; //ms
  constexpr const size_t UART_TX_CHUNK_SIZE = CONF_UART_TX_CHUNK_SIZE;
  constexpr const size_t MESSAGE_MNEMONICS_CAPACITY = CONF_MESSAGE_MNEMONICS_CAPACITY;
  constexpr const uint32_t MESSAGE_UPDATE_INTERVAL = CONF_MESSAGE_UPDATE_INTERVAL; //ms
  constexpr const uint32_t MESSAGE_UPDATE_TIMEOUT = CONF_MESSAGE_UPDATE_TIMEOUT; // ms
  constexpr const bool MESSAGE_STS_PROMOTE = CONF_MESSAGE_STS_PROMOTE;
  constexpr const bool MESSAGE_BUZZER = CONF_MESSAGE_BUZZER;
  constexpr const bool MESSAGE_CMD_RAW = CONF_MESSAGE_CMD_RAW;
  //constexpr const uint8_t MESSAGE_STS_QOS = CONF_MESSAGE_STS_QOS;
  //constexpr const uint8_t MESSAGE_CMD_QOS = CONF_MESSAGE_CMD_QOS;

  constexpr const size_t MESSAGE_SIZE_MIN = 54; //len('.{{"TtIN":1,"MsgN":1,"DataN":1}{"Res":0}{"ChS":64815}}')
  constexpr const char* const MESSAGE_HEAD = "\x02{{\"TtIN\":1,\"MsgN\":1,\"DataN\":";
  constexpr const size_t MESSAGE_HEAD_SIZE = 29;
  constexpr const struct {char start, end;} MESSAGE_BOUNDARIES {0x02, 0x03};

  constexpr const struct {uint8_t min, max;} MESSAGE_BUFFER_KEY_SIZE {4, 9};
  constexpr const struct {uint8_t min, max;} MESSAGE_BUFFER_VALUE_SIZE {1, 25};
  constexpr const struct {uint8_t min, max;} MESSAGE_BUFFER_ITEM_SIZE {
    MESSAGE_BUFFER_KEY_SIZE.min+ MESSAGE_BUFFER_VALUE_SIZE.min, 
    MESSAGE_BUFFER_KEY_SIZE.max+ MESSAGE_BUFFER_VALUE_SIZE.max
  };
  constexpr const size_t MESSAGE_BUFFER_SIZE = (50 + MESSAGE_MNEMONICS_CAPACITY * MESSAGE_BUFFER_VALUE_SIZE.max + 16);

  constexpr const size_t MNEMONIC_BUFFER_SIZE = 32;
  constexpr const bool MNEMONIC_BUFFER_NULL_TERMINATED = true;
  constexpr const struct {uint8_t min, max;}  MNEMONIC_NAME_SIZE = {2, 6};
  constexpr const uint8_t MNEMONIC_FLOAT_PRECISION = 1;
}
}