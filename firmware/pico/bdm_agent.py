"""Agent MicroPython du Pico : pilote BDM PIO sur J33 et boucle USB.

Toutes les broches restent en haute impédance tant que le +3V3S n'est pas validé.
Câblage : DSCLK GP2, DSI GP3, DSO GP4, BKPT GP5, RESET GP6, ALLPST GP7, +3V3S GP26.
"""

import sys
import time

import rp2
from machine import ADC, Pin

from bdm_protocol import Agent

DSCLK, DSI, DSO, BKPT, RESET, ALLPST = 2, 3, 4, 5, 6, 7
SENSE_ADC = 26
SM_FREQ = 200_000  # 8 cycles par bit : 25 kHz sur DSCLK, validé sur le BP ; ajustable par Hardware(freq)


@rp2.asm_pio(
    sideset_init=rp2.PIO.OUT_LOW,
    out_init=rp2.PIO.OUT_LOW,
    out_shiftdir=rp2.PIO.SHIFT_LEFT,
    in_shiftdir=rp2.PIO.SHIFT_LEFT,
)
def bdm_17_bits():
    pull(block).side(0)
    set(x, 16).side(0)
    label("bit")
    out(pins, 1).side(0)[2]
    nop().side(1)[2]
    in_(pins, 1).side(1)
    jmp(x_dec, "bit").side(0)
    push(block).side(0)


class Hardware:
    def __init__(self, freq=SM_FREQ):
        self.freq = freq
        self.adc = ADC(SENSE_ADC)
        self.sm = None
        self._release()

    def _release(self):
        for n in (DSCLK, DSI, DSO, BKPT, RESET, ALLPST):
            Pin(n, Pin.IN)

    def sense_mv(self):
        return self.adc.read_u16() * 3300 // 65535

    def start_and_halt(self):
        reset = Pin(RESET, Pin.OPEN_DRAIN, value=0)
        Pin(BKPT, Pin.OUT, value=0)
        self.sm = rp2.StateMachine(
            0,
            bdm_17_bits,
            freq=self.freq,
            sideset_base=Pin(DSCLK),
            out_base=Pin(DSI),
            in_base=Pin(DSO, Pin.IN),
        )
        self.sm.active(1)
        time.sleep_ms(20)
        reset.value(1)
        Pin(RESET, Pin.IN)
        time.sleep_ms(50)
        Pin(BKPT, Pin.OUT, value=1)
        return Pin(ALLPST, Pin.IN).value()

    def exchange(self, word):
        self.sm.put((word & 0x1FFFF) << 15)
        return self.sm.get() & 0x1FFFF

    def stop(self):
        if self.sm is not None:
            self.sm.active(0)
            self.sm = None
        self._release()


def run():
    hw = Hardware()
    agent = Agent(hw)
    print("READY")
    try:
        while True:
            line = sys.stdin.readline()
            if not line.strip():
                continue  # reste du retour chariot de la REPL, sans réponse
            if line.strip() == "QUIT":
                print("OK")
                return
            print(agent.handle(line))
    finally:
        hw.stop()
