"""Agent BDM en lecture seule : logique sans matériel (MicroPython et CPython).

Cette liste blanche est la barrière d'écriture : tout mot BDM envoyé à la cible
passe par `_command`. N'y ajouter aucun opcode WRITE, FILL, WDMREG ou WAREG.
"""

try:
    import ubinascii as binascii
except ImportError:
    import binascii

NOP = 0x0000
GO = 0x0C00
READ_LONG = 0x1980
RDMREG_CSR = 0x2D80
ALLOWED_OPCODES = (NOP, GO, READ_LONG, RDMREG_CSR)

FLASH_SIZE = 0x80000
MAX_READ = 1024
MAX_POLLS = 1000
SENSE_MIN_MV = 3000
SENSE_MAX_MV = 3600

S_FLAG = 0x10000
NOT_READY = 0x10000
BUS_ERROR = 0x10001
ILLEGAL = 0x1FFFF


class BdmError(Exception):
    pass


class Agent:
    """Traite une ligne de commande USB ; `hw` porte les accès aux broches."""

    def __init__(self, hw):
        self.hw = hw
        self.started = False

    def _command(self, opcode):
        if opcode not in ALLOWED_OPCODES:
            raise BdmError("OPCODE")
        return self.hw.exchange(opcode)

    def _reply_word(self):
        for _ in range(MAX_POLLS):
            r = self._command(NOP)
            if r == NOT_READY:
                continue
            if r == BUS_ERROR:
                raise BdmError("BUS")
            if r == ILLEGAL:
                raise BdmError("ILLEGAL")
            if r & S_FLAG:
                raise BdmError("STATUS %05X" % r)
            return r & 0xFFFF
        raise BdmError("TIMEOUT")

    def _reply_long(self):
        hi = self._reply_word()
        return (hi << 16) | self._reply_word()

    def _read_long(self, address):
        self._command(READ_LONG)
        # Les mots d'extension sont des données, pas des opcodes.
        self.hw.exchange((address >> 16) & 0xFFFF)
        self.hw.exchange(address & 0xFFFF)
        return self._reply_long()

    def _read(self, address, length):
        if address % 4 or length % 4 or length <= 0 or length > MAX_READ:
            raise BdmError("ALIGN")
        if address < 0 or address + length > FLASH_SIZE:
            raise BdmError("RANGE")
        out = bytearray()
        for a in range(address, address + length, 4):
            v = self._read_long(a)
            out.extend(bytes(((v >> 24) & 255, (v >> 16) & 255, (v >> 8) & 255, v & 255)))
        return out

    def _require_started(self):
        if not self.started:
            raise BdmError("NOT_STARTED")

    def _powered(self):
        mv = self.hw.sense_mv()
        return mv, SENSE_MIN_MV <= mv <= SENSE_MAX_MV

    def handle(self, line):
        parts = line.strip().split()
        if not parts:
            return "ERR EMPTY"
        try:
            return self._dispatch(parts[0], parts[1:])
        except BdmError as exc:
            return "ERR %s" % exc
        except ValueError:
            return "ERR ARGS"

    def _dispatch(self, cmd, args):
        if cmd == "PING":
            return "OK PONG"
        if cmd == "SENSE":
            return "OK %d %d" % (self._powered()[0], self._powered()[1])
        if cmd == "HALT":
            mv, ok = self._powered()
            if not ok:
                return "ERR NO_POWER %d" % mv
            allpst = self.hw.start_and_halt()
            self.started = True
            return "OK %d" % allpst
        if cmd == "CSR":
            self._require_started()
            self._command(RDMREG_CSR)
            csr = self._reply_long()
            if csr in (0, 0xFFFFFFFF):
                raise BdmError("NO_LINK %08X" % csr)
            return "OK %08X" % csr
        if cmd == "READ":
            self._require_started()
            if len(args) != 2:
                return "ERR ARGS"
            data = self._read(int(args[0], 16), int(args[1], 16))
            return "OK " + binascii.hexlify(data).decode()
        if cmd == "GO":
            self._require_started()
            self._command(GO)
            if self._reply_word() != 0xFFFF:
                raise BdmError("GO_NOT_ACKED")
            self.hw.stop()
            self.started = False
            return "OK"
        if cmd == "STOP":
            self.hw.stop()
            self.started = False
            return "OK"
        return "ERR UNKNOWN"
