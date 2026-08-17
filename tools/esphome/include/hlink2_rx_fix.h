#pragma once

#include <stdint.h>

// LibreTiny's SerialClass::begin() first calls beginPrivate(), which enables the
// AmebaZ UART receive path and the RX data interrupt, and only then calls
// configure() -> UART_Init(), which resets the interrupt enable register and the
// RX path again. Transmission is unaffected, but the UART never receives a byte.
// This re-enables both after the ESPHome UART component has been set up.
// The AmebaZ SDK headers are not C++ clean, so the implementation is a C file.

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
  uint32_t intcr_before;
  uint32_t rx_path_before;
  uint32_t lcr;
  uint32_t lsr;
  uint32_t intcr_after;
  uint32_t rx_path_after;
} Hlink2RxFixResult;

Hlink2RxFixResult hlink2_reenable_uart0_rx(void);

// ArduinoCore-API's RingBuffer keeps a shared element counter. UART0 increments
// it from an ISR while ESPHome decrements it from the main loop; both operations
// are non-atomic on AmebaZ. Mask only UART0's IRQ while available()+read() drain
// the software buffer so that the counter cannot be permanently corrupted.
void hlink2_uart0_rx_critical_enter(void);
void hlink2_uart0_rx_critical_exit(void);

#ifdef __cplusplus
}
#endif
