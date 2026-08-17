#include "hlink2_rx_fix.h"

// The AmebaZ SDK headers cannot be included here: every file in src/ is built with
// "-include Arduino.h", and basic_types.h then redefines bool/boolean. Only the two
// ROM routines and the UART0 register layout are needed, so both are declared
// locally. Values are taken from hal_platform.h and rtl8711b_uart.h.

#define HLINK2_UART0_REG_BASE 0x40040000u
#define HLINK2_UART0_IRQ 8
#define HLINK2_UART0_IRQ_PRIORITY 10u
#define HLINK2_ENABLE 1u
#define HLINK2_RUART_IER_ERBI 0x00000001u

typedef struct {
  volatile uint32_t DLL;        // 0x00
  volatile uint32_t DLH_INTCR;  // 0x04 interrupt enable register
  volatile uint32_t INTID;      // 0x08
  volatile uint32_t LCR;        // 0x0C line control
  volatile uint32_t MCR;        // 0x10
  volatile uint32_t LSR;        // 0x14 line status
  volatile uint32_t MDSR;       // 0x18
  volatile uint32_t SPR;        // 0x1C
  volatile uint32_t STSR;       // 0x20
  volatile uint32_t RB_THR;     // 0x24
  volatile uint32_t MISCR;      // 0x28
  volatile uint32_t TXPLSR;     // 0x2C
  volatile uint32_t RXPLSR;     // 0x30
  volatile uint32_t BAUDMONR;   // 0x34
  volatile uint32_t RSVD2;      // 0x38
  volatile uint32_t DBG_UART;   // 0x3C
  volatile uint32_t RX_PATH;    // 0x40 rx path control
} Hlink2UartRegs;

extern void UART_RxCmd(void *uart, uint32_t new_state) __attribute__((long_call));
extern void UART_INTConfig(void *uart, uint32_t uart_it, uint32_t new_state) __attribute__((long_call));
extern void VECTOR_IrqDis(int32_t irq) __attribute__((long_call));
extern void VECTOR_IrqEn(int32_t irq, uint32_t priority) __attribute__((long_call));

Hlink2RxFixResult hlink2_reenable_uart0_rx(void) {
  Hlink2UartRegs *uart = (Hlink2UartRegs *) HLINK2_UART0_REG_BASE;
  Hlink2RxFixResult result;

  result.intcr_before = uart->DLH_INTCR;
  result.rx_path_before = uart->RX_PATH;
  result.lcr = uart->LCR;
  result.lsr = uart->LSR;

  UART_RxCmd((void *) uart, HLINK2_ENABLE);
  UART_INTConfig((void *) uart, HLINK2_RUART_IER_ERBI, HLINK2_ENABLE);

  result.intcr_after = uart->DLH_INTCR;
  result.rx_path_after = uart->RX_PATH;
  return result;
}

void hlink2_uart0_rx_critical_enter(void) {
  VECTOR_IrqDis(HLINK2_UART0_IRQ);
}

void hlink2_uart0_rx_critical_exit(void) {
  VECTOR_IrqEn(HLINK2_UART0_IRQ, HLINK2_UART0_IRQ_PRIORITY);
}
