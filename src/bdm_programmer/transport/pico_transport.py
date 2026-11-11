"""Accès en lecture seule au BP via l'agent Pico (voir firmware/pico).

Volontairement indépendant de `BdmTransport` : cette classe n'a aucune
opération d'effacement ni d'écriture.
"""

from __future__ import annotations

CHUNK = 1024


class PicoError(RuntimeError):
    """L'agent Pico a refusé une commande ou n'a pas répondu."""


class TargetNotPowered(PicoError):
    """Le +3V3S de la carte est absent ou hors plage."""


class PicoReadOnlyTransport:
    def __init__(self, port) -> None:
        self._port = port

    def connect(self) -> None:
        """Lance l'agent puis vérifie le +3V3S, sans piloter la cible."""
        self._port.write(b"\x03\r\nimport bdm_agent; bdm_agent.run()\r\n")
        for _ in range(200):
            line = self._port.readline()
            if line.strip() == b"READY":
                break
        else:
            raise PicoError("agent Pico absent : copier firmware/pico/*.py sur le Pico")
        mv, ok = self._ask("SENSE").split()
        if ok != "1":
            raise TargetNotPowered(f"+3V3S hors plage : {mv} mV, carte non alimentée ?")

    def _ask(self, command: str) -> str:
        self._port.write(command.encode() + b"\r\n")
        reply = self._port.readline().decode(errors="replace").strip()
        if reply == "OK":
            return ""
        if reply.startswith("OK "):
            return reply[3:]
        raise PicoError(f"{command.split()[0]} : {reply or 'pas de réponse'}")

    def halt(self) -> None:
        self._ask("HALT")

    def read_csr(self) -> int:
        return int(self._ask("CSR"), 16)

    def read_memory(self, address: int, length: int) -> bytes:
        out = bytearray()
        for offset in range(0, length, CHUNK):
            size = min(CHUNK, length - offset)
            out += bytes.fromhex(self._ask(f"READ {address + offset:X} {size:X}"))
        return bytes(out)

    def resume(self) -> None:
        self._ask("GO")

    def release(self) -> None:
        """Remet les broches du Pico en haute impédance."""
        self._ask("STOP")

    def disconnect(self) -> None:
        self._port.write(b"QUIT\r\n")
