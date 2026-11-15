#!/usr/bin/env python3
"""Génère le schéma KiCad 10 de la carte de diagnostic BP (``carte-diagnostic-bp.kicad_sch``).

Feature carte-diagnostic-bp-2026-11-009 (essensys-hub/essensys-feature-lifecycle#67), tâche 1.3.
Le circuit est décrit par la table ``PARTS`` (broche -> net). Chaque broche reçoit un court fil
et une étiquette de net : le schéma est exact et vérifiable (ERC, ``check_netlist.py``),
la mise en page reste utilitaire.

Usage : ``python3 hardware/carte-diagnostic-bp/gen_sch.py`` (KiCad 10 installé).
Utilitaires S-expression repris de essensys-i2c-ba-sniffer/hardware/kicad/gen_sch.py.
"""

import copy
import os
import uuid

KSYM = os.environ.get("KICAD9_SYMBOL_DIR", "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols") + "/"
OUT = os.path.dirname(os.path.abspath(__file__))
NAME = "carte-diagnostic-bp"
U = lambda s: str(uuid.uuid5(uuid.NAMESPACE_URL, "essensys-bdm-programmer/carte-diagnostic-bp/" + s))  # noqa: E731
ROOT = U("root")
G = 2.54


# ---------- S-expression ----------
def tok(s):
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c in "()":
            yield c
            i += 1
        elif c.isspace():
            i += 1
        elif c == '"':
            j = i + 1
            buf = []
            while s[j] != '"':
                if s[j] == "\\":
                    buf.append(s[j:j + 2])
                    j += 2
                else:
                    buf.append(s[j])
                    j += 1
            yield ("S", "".join(buf))
            i = j + 1
        else:
            j = i
            while j < n and not s[j].isspace() and s[j] not in "()":
                j += 1
            yield s[i:j]
            i = j


def parse(s):
    st = [[]]
    for t in tok(s):
        if t == "(":
            st.append([])
        elif t == ")":
            x = st.pop()
            st[-1].append(x)
        else:
            st[-1].append(t)
    return st[0]


def dump(x, ind=0):
    if isinstance(x, tuple):
        return '"' + x[1] + '"'
    if isinstance(x, str):
        return x
    if all(not isinstance(e, list) for e in x):
        return "(" + " ".join(dump(e) for e in x) + ")"
    pad = "\t" * (ind + 1)
    return "(" + dump(x[0]) + "".join("\n" + pad + dump(e, ind + 1) for e in x[1:]) + "\n" + "\t" * ind + ")"


def S(v):
    return ("S", v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n"))


def f(v):
    return ("%.3f" % v).rstrip("0").rstrip(".")


_libs = {}


def lib(name):
    if name not in _libs:
        _libs[name] = parse(open(KSYM + name + ".kicad_sym").read())[0]
    return _libs[name]


def find_sym(libname, sym):
    for e in lib(libname):
        if isinstance(e, list) and e[0] == "symbol" and e[1][1] == sym:
            return copy.deepcopy(e)
    raise KeyError(sym)


def flat_sym(libname, sym):
    s = find_sym(libname, sym)
    ext = [e for e in s if isinstance(e, list) and e[0] == "extends"]
    if not ext:
        return s
    parent = flat_sym(libname, ext[0][1][1])
    pname = parent[1][1]
    parent[1] = S(sym)
    childprops = {e[1][1]: e for e in s if isinstance(e, list) and e[0] == "property"}
    for i, e in enumerate(parent):
        if isinstance(e, list) and e[0] == "property" and e[1][1] in childprops:
            parent[i] = childprops[e[1][1]]
        if isinstance(e, list) and e[0] == "symbol":
            e[1] = S(e[1][1].replace(pname, sym, 1))
    return parent


def pins_of(sym):
    """num -> (x, y, angle, unit) ; ignore la représentation De Morgan (style 2)."""
    res = {}

    def walk(x, unit):
        for e in x:
            if isinstance(e, list):
                if e[0] == "symbol" and isinstance(e[1], tuple):
                    parts = e[1][1].rsplit("_", 2)
                    if len(parts) == 3 and parts[2] == "2":
                        continue
                    walk(e, int(parts[1]) if len(parts) == 3 else unit)
                elif e[0] == "pin":
                    at = [a for a in e if isinstance(a, list) and a[0] == "at"][0]
                    num = [a for a in e if isinstance(a, list) and a[0] == "number"][0][1][1]
                    if num not in res:
                        res[num] = (float(at[1]), float(at[2]), int(float(at[3])), unit)
                else:
                    walk(e, unit)

    walk(sym, 0)
    return res


def fx(size=1.27, hide=False, j=None):
    e = ["effects", ["font", ["size", f(size), f(size)]]]
    if j:
        e.append(["justify"] + j)
    if hide:
        e.append(["hide", "yes"])
    return e


libsyms, pinmap = [], {}


def need(lid):
    if lid in pinmap:
        return
    lname, sname = lid.split(":")
    sy = flat_sym(lname, sname)
    pinmap[lid] = pins_of(sy)
    sy[1] = S(lid)
    libsyms.append(sy)


items = []


def text(t, x, y, size=1.27, n=None, bold=False):
    font = ["font", ["size", f(size), f(size)]] + ([["bold", "yes"]] if bold else [])
    items.append(["text", S(t), ["exclude_from_sim", "no"], ["at", f(x), f(y), "0"],
                  ["effects", font, ["justify", "left", "bottom"]], ["uuid", U("t/" + (n or t[:40]))]])


# ================= Carte de diagnostic BP =================
ROT = {0: lambda dx, dy: (dx, dy)}
_w = [0]


def place(lid, ref, val, fp, x, y, unit=1, extra=None):
    need(lid)
    props = [["property", S("Reference"), S(ref), ["at", f(x), f(y - 2.54), "0"], fx(j=["left"], hide=ref.startswith("#"))],
             ["property", S("Value"), S(val), ["at", f(x), f(y + 2.54), "0"], fx(j=["left"])],
             ["property", S("Footprint"), S(fp), ["at", f(x), f(y), "0"], fx(hide=True)],
             ["property", S("Datasheet"), S(""), ["at", f(x), f(y), "0"], fx(hide=True)]]
    for k, v in (extra or {}).items():
        props.append(["property", S(k), S(v), ["at", f(x), f(y), "0"], fx(hide=True)])
    upins = [p for p, d in pinmap[lid].items() if d[3] in (0, unit)]
    items.append(["symbol", ["lib_id", S(lid)], ["at", f(x), f(y), "0"], ["unit", str(unit)],
                  ["exclude_from_sim", "no"], ["in_bom", "yes"], ["on_board", "yes"], ["dnp", "no"],
                  ["uuid", U("sym/%s/%d" % (ref, unit))]] + props +
                 [["pin", S(p), ["uuid", U("pin/%s/%s" % (ref, p))]] for p in upins] +
                 [["instances", ["project", S(NAME), ["path", S("/" + ROOT), ["reference", S(ref)], ["unit", str(unit)]]]]])
    return {p: (round(x + pinmap[lid][p][0], 3), round(y - pinmap[lid][p][1], 3), pinmap[lid][p][2]) for p in upins}


OUTWARD = {0: (-1, 0, 180), 180: (1, 0, 0), 90: (0, 1, 270), 270: (0, -1, 90)}  # angle de broche -> (dx, dy, angle étiquette)


def connect(ref, pins, nets):
    """Pose un fil court et une étiquette sur chaque broche, ou un drapeau « non connecté »."""
    for p, (x, y, a) in sorted(pins.items()):
        if p not in nets:
            raise KeyError("%s.%s sans net" % (ref, p))
        net = nets[p]
        if net is None:
            items.append(["no_connect", ["at", f(x), f(y)], ["uuid", U("nc/%s/%s" % (ref, p))]])
            continue
        dx, dy, la = OUTWARD[a]
        x2, y2 = round(x + dx * 2.54, 3), round(y + dy * 2.54, 3)
        _w[0] += 1
        items.append(["wire", ["pts", ["xy", f(x), f(y)], ["xy", f(x2), f(y2)]],
                      ["stroke", ["width", "0"], ["type", "default"]], ["uuid", U("wire/%s/%s" % (ref, p))]])
        just = ["right", "bottom"] if la == 180 else ["left", "bottom"]
        items.append(["label", S(net), ["at", f(x2), f(y2), str(la)], fx(j=just), ["uuid", U("lab/%s/%s" % (ref, p))]])
    extra = set(nets) - set(pins)
    if extra:
        raise KeyError("%s : broches inconnues %s" % (ref, sorted(extra)))


def text(t, x, y, size=1.27, n=None, bold=False):
    font = ["font", ["size", f(size), f(size)]] + ([["bold", "yes"]] if bold else [])
    items.append(["text", S(t), ["exclude_from_sim", "no"], ["at", f(x), f(y), "0"],
                  ["effects", font, ["justify", "left", "bottom"]], ["uuid", U("t/" + (n or t[:40]))]])


R0603, C0603 = "Resistor_SMD:R_0603_1608Metric", "Capacitor_SMD:C_0603_1608Metric"
GND = "GND"
BDM = ["DSCLK", "DSI", "DSO", "BKPT", "RESET", "ALLPST"]  # ordre des GP2..GP7 du Pico (feature 005)
J33 = {"BKPT": "2", "DSO": "3", "DSI": "4", "ALLPST": "5", "DSCLK": "6", "RESET": "8"}

# (ref, lib_id, valeur, empreinte, x, y, {broche: net | None}, LCSC ou note, unités)
PARTS = []


def part(ref, lid, val, fp, x, y, nets, lcsc="", units=(1,)):
    PARTS.append((ref, lid, val, fp, round(x / 2.54) * 2.54, round(y / 2.54) * 2.54, nets, lcsc, units))


# --- USB-C, protection, hub, régulateur ---
part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C", "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", 40, 60,
     {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A1": GND, "A12": GND, "B1": GND, "B12": GND, "SH": GND,
      "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DM", "B7": "USB_DM", "A8": None, "B8": None}, "C709357")
part("U5", "Power_Protection:USBLC6-2SC6", "USBLC6-2SC6", "Package_TO_SOT_SMD:SOT-23-6", 100, 50,
     {"1": "USB_DM", "6": "USB_DM", "3": "USB_DP", "4": "USB_DP", "2": GND, "5": "VBUS"}, "C5261088")
part("U2", "Interface_USB:CH334R", "CH334R", "Package_SO:QSOP-16_3.9x4.9mm_P0.635mm", 160, 60,
     {"10": "USB_DM", "11": "USB_DP", "12": "VBUS", "13": "HUB_3V3", "14": GND, "15": "HUB_XO", "16": "HUB_XI", "9": None,
      "8": "PICO_DP", "7": "PICO_DM", "6": "ANA_HUB_DP", "5": "ANA_HUB_DM", "4": None, "3": None, "2": None, "1": None}, "C4154405")
part("Y2", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", 160, 110,
     {"1": "HUB_XI", "3": "HUB_XO", "2": GND, "4": GND}, "C276421")
part("U3", "Regulator_Linear:AMS1117-3.3", "AMS1117-3.3", "Package_TO_SOT_SMD:SOT-223-3_TabPin2", 220, 50,
     {"3": "VBUS", "2": "+3V3", "1": GND}, "C6186")

# --- module Pico (BDM) et port J33 ---
pico = {str(n): None for n in range(1, 41)}
pico.update({str(n): GND for n in (3, 8, 13, 18, 23, 28, 38)})  # 33 (AGND) et TP1 : déjà reliés au GND sur le module, laissés libres pour l'ERC
pico.update({"4": "P_DSCLK", "5": "P_DSI", "6": "P_DSO", "7": "P_BKPT", "9": "P_RESET", "10": "P_ALLPST", "31": "SENSE_3V3S", "40": "VBUS",
             "TP1": None, "TP2": "PICO_DM", "TP3": "PICO_DP", "TP4": None, "TP5": None, "TP6": None, "D1": None, "D2": GND, "D3": None})
part("A1", "MCU_Module:RaspberryPi_Pico_Extensive", "Pico (BDM)", "Module:RaspberryPi_Pico_SMD", 70, 190, pico, "soudé à la main")
j2 = {"1": None, "7": "J33_3V3S", "9": GND, "10": GND}
j2.update({pin: "J33_" + s for s, pin in J33.items()})
part("J2", "Connector_Generic:Conn_02x05_Odd_Even", "Nappe vers J33 du BP", "Connector_IDC:IDC-Header_2x05_P2.54mm_Vertical", 160, 180, j2, "soudé à la main")

# --- analyseur RP2040 ---
u1 = {str(n): None for n in range(1, 57)}
u1.update({str(n): "+3V3" for n in (1, 10, 22, 33, 42, 49, 43, 44, 48)})
u1.update({"23": "+1V1", "50": "+1V1", "45": "+1V1", "57": GND, "19": GND, "20": "ANA_XIN", "21": "ANA_XOUT", "24": "ANA_SWCLK", "25": "ANA_SWDIO",
           "26": "ANA_RUN", "46": "ANA_DM", "47": "ANA_DP", "56": "QSPI_SS", "52": "QSPI_SCLK", "53": "QSPI_SD0", "55": "QSPI_SD1",
           "54": "QSPI_SD2", "51": "QSPI_SD3", "4": "SCL_OUT", "5": "SDA_OUT", "37": "ANA_LED"})
for i, s in enumerate(BDM):  # GPIO4..GPIO9 = broches 6, 7, 8, 9, 11, 12
    u1[("6", "7", "8", "9", "11", "12")[i]] = "A_" + s
part("U1", "MCU_RaspberryPi:RP2040", "RP2040 (analyseur)", "Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm", 330, 150, u1, "C2040")
part("U6", "Memory_Flash:W25Q16JVSS", "W25Q16JVSS", "Package_SO:SOIC-8_5.3x5.3mm_P1.27mm", 450, 70,
     {"1": "QSPI_SS", "2": "QSPI_SD1", "3": "QSPI_SD2", "4": GND, "5": "QSPI_SD0", "6": "QSPI_SCLK", "7": "QSPI_SD3", "8": "+3V3"}, "C131025")
part("Y1", "Device:Crystal_GND24", "12MHz", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm", 450, 120,
     {"1": "ANA_XIN", "3": "ANA_XOUT_X", "2": GND, "4": GND}, "C276421")
part("SW1", "Switch:SW_Push", "BOOTSEL", "Button_Switch_SMD:SW_SPST_TL3342", 450, 160, {"1": "BOOT_SW", "2": GND}, "non monté : référence et empreinte à figer")
part("J5", "Connector_Generic:Conn_01x03", "SWD analyseur", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", 450, 200,
     {"1": "ANA_SWCLK", "2": GND, "3": "ANA_SWDIO"}, "non monté")
part("D5", "Device:LED", "Activité", "LED_SMD:LED_0603_1608Metric", 450, 240, {"2": "ANA_LED_R", "1": GND}, "C72043")

# --- port de diagnostic I2C ---
MPC3 = "Connector_Molex:Molex_Micro-Fit_3.0_43045-0412_2x02_P3.00mm_Vertical"  # empreinte à confronter au plan Würth 66200421122
for ref, x in (("J3", 250), ("J4", 300)):
    part(ref, "Connector_Generic:Conn_02x02_Odd_Even", "Bus I2C (passage)", MPC3, x, 320,
         {"1": "BUS_SDA", "2": "BUS_SCL", "3": "BUS_0V", "4": "BUS_15V"}, "Würth 66200421122, soudé à la main")
part("U4", "74xGxx:74LVC2G17", "SN74LVC2G17", "Package_TO_SOT_SMD:SOT-23-6", 360, 320,
     {"1": "SCL_IN", "6": "SCL_OUT", "3": "SDA_IN", "4": "SDA_OUT", "5": "+3V3", "2": GND}, "C10429", units=(1, 2, 3))
part("D1", "Device:D_Zener", "5V1", "Diode_SMD:D_SOD-123", 460, 300, {"1": "SCL_IN", "2": GND}, "C19077401")
part("D2", "Device:D_Zener", "5V1", "Diode_SMD:D_SOD-123", 480, 300, {"1": "SDA_IN", "2": GND}, "C19077401")
part("F1", "Device:Polyfuse", "50mA 60V", "Fuse:Fuse_1206_3216Metric", 500, 300, {"1": "BUS_0V", "2": GND}, "C2830235")
part("D3", "Device:LED", "Erreur de branchement", "LED_SMD:LED_0603_1608Metric", 520, 300, {"2": "FAULT_A", "1": GND}, "C72043")
part("D4", "Device:D", "1N4148W", "Diode_SMD:D_SOD-123", 540, 300, {"1": "FAULT_A", "2": GND}, "C81598")

# --- résistances et condensateurs (rangées automatiques) ---
RS = [("R1", "5k1", "CC1", GND), ("R2", "5k1", "CC2", GND), ("R3", "27", "ANA_DM", "ANA_HUB_DM"), ("R4", "27", "ANA_DP", "ANA_HUB_DP"),
      ("R5", "1k", "ANA_XOUT", "ANA_XOUT_X"), ("R6", "1k", "QSPI_SS", "BOOT_SW"), ("R7", "10k", "ANA_RUN", "+3V3"), ("R8", "1k", "ANA_LED", "ANA_LED_R"),
      ("R16", "10k", "J33_3V3S", "SENSE_3V3S"), ("R17", "1M", "SENSE_3V3S", GND),
      ("R20", "100k", "BUS_SCL", "SCL_IN"), ("R21", "100k", "BUS_SDA", "SDA_IN"), ("R22", "4k7", "BUS_0V", "FAULT_A")]
RS += [("R%d" % (10 + i), "100", "P_" + s, "J33_" + s) for i, s in enumerate(BDM)]
RS += [("R%d" % (30 + i), "1k", "J33_" + s, "A_" + s) for i, s in enumerate(BDM)]
CS = [("C1", "10u", "VBUS"), ("C2", "22u", "+3V3"), ("C10", "1u", "+3V3"), ("C11", "1u", "+1V1"), ("C12", "100n", "+1V1"), ("C13", "100n", "+1V1"),
      ("C14", "100n", "+3V3"), ("C15", "100n", "+3V3"), ("C16", "15p", "ANA_XIN"), ("C17", "15p", "ANA_XOUT_X"),
      ("C18", "1u", "HUB_3V3"), ("C19", "100n", "HUB_3V3"), ("C20", "100n", "VBUS")]
CS += [("C%d" % n, "100n", "+3V3") for n in range(3, 10)]
# références LCSC des passifs 0603, vérifiées le 2026-11-15 dans l'index du catalogue JLCPCB
R_LCSC = {"27": "C25190", "100": "C22775", "1k": "C21190", "4k7": "C23162", "5k1": "C23186", "10k": "C25804", "100k": "C25803", "1M": "C22935"}
C_LCSC = {"15p": "C1644", "100n": "C14663", "1u": "C15849", "10u": "C19702", "22u": "C59461"}
for i, (ref, val, a, b) in enumerate(sorted(RS, key=lambda r: int(r[0][1:]))):
    part(ref, "Device:R", val, R0603, 30 + 17.78 * (i % 28), 370, {"1": a, "2": b}, R_LCSC[val])
for i, (ref, val, net) in enumerate(sorted(CS, key=lambda c: int(c[0][1:]))):
    part(ref, "Device:C", val, C0603, 30 + 17.78 * (i % 28), 400, {"1": net, "2": GND}, C_LCSC[val])

for ref, lid, val, fp, x, y, nets, lcsc, units in PARTS:
    seen = {}
    for k, u in enumerate(units):
        seen.update(place(lid, ref, val, fp, x + 35.56 * k, y, unit=u, extra={"LCSC": lcsc}))
    connect(ref, seen, nets)

text("CARTE DE DIAGNOSTIC BP — BDM J33 (Pico) et espion I2C (RP2040) derrière un seul USB-C", 20, 20, 2.5, n="titre", bold=True)
text("Lecture seule. Broche 1 de J33 non connectée, +3V3S mesuré seulement. Port I2C : chaque broche tolère 15 V.\n"
     "Ne jamais brancher le micro-USB du module Pico : son USB passe par les pastilles TP2/TP3 vers le hub.", 20, 30, 1.5, n="regles")
for t, x, y in (("USB, HUB, ALIMENTATION", 20, 40), ("PICO BDM ET PORT J33", 20, 140), ("ANALYSEUR RP2040", 270, 40),
                ("PORT DE DIAGNOSTIC I2C (PROTÉGÉ)", 240, 295), ("RÉSISTANCES", 20, 360), ("CONDENSATEURS", 20, 390)):
    text(t, x, y, 1.8, n=t, bold=True)

sch = ["kicad_sch", ["version", "20250114"], ["generator", S("eeschema")], ["generator_version", S("9.0")],
       ["uuid", ROOT], ["paper", S("A2")],
       ["title_block", ["title", S("Carte de diagnostic BP")], ["date", S("2026-11-15")], ["rev", S("A")],
        ["company", S("Essensys – essensys-bdm-programmer")],
        ["comment", "1", S("Feature: carte-diagnostic-bp-2026-11-009 – Refs essensys-hub/essensys-feature-lifecycle#67")],
        ["comment", "2", S("Usage sur banc uniquement, jamais sur une armoire réelle")]],
       ["lib_symbols"] + libsyms] + items + [["sheet_instances", ["path", S("/"), ["page", S("1")]]], ["embedded_fonts", "no"]]
open(os.path.join(OUT, NAME + ".kicad_sch"), "w").write(dump(sch) + "\n")
row = '\t(lib (name "%s")(type "KiCad")(uri "%s")(options "")(descr ""))\n'
open(os.path.join(OUT, "sym-lib-table"), "w").write("(sym_lib_table\n\t(version 7)\n" + "".join(
    row % (n, "${KICAD9_SYMBOL_DIR}/%s.kicad_sym" % n) for n in sorted({l.split(":")[0] for l in pinmap})) + ")\n")
open(os.path.join(OUT, "fp-lib-table"), "w").write("(fp_lib_table\n\t(version 7)\n" + "".join(
    row % (n, "${KICAD9_FOOTPRINT_DIR}/%s.pretty" % n) for n in sorted({p[3].split(":")[0] for p in PARTS})) + ")\n")
import json  # noqa: E402

open(os.path.join(OUT, NAME + ".kicad_pro"), "w").write(json.dumps(
    {"meta": {"filename": NAME + ".kicad_pro", "version": 3}, "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
     # règles de fabrication : capacités JLCPCB 4 couches (piste et isolement 0,09 mm mini, via 0,3/0,6 mm), avec marge
     "board": {"design_settings": {"rules": {"min_track_width": 0.1, "min_clearance": 0.127, "min_via_diameter": 0.6,
                                             "min_through_hole_diameter": 0.3, "min_copper_edge_clearance": 0.3}}},
     "net_settings": {"classes": [{"name": "Default", "clearance": 0.15, "track_width": 0.15, "via_diameter": 0.6, "via_drill": 0.3,
                                   "priority": 2147483647, "schematic_color": "rgba(0, 0, 0, 0.000)", "pcb_color": "rgba(0, 0, 0, 0.000)",
                                   "line_style": 0, "wire_width": 6, "bus_width": 12, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                                   "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25}],
                      "meta": {"version": 4}},
     "sheets": [[ROOT, "Root"]], "text_variables": {}}, indent=2) + "\n")
print("ok", NAME, len(PARTS), "composants")
