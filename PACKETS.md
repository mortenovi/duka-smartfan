# Every byte, and what it actually does

This is the wire format of a call to the fan, byte by byte, with each byte verified against the unit rather than copied from a datasheet.

**The call never leaves your network.** The packet goes to the fan's own address on the local network, UDP port 4000. No hostname is looked up and no vendor server is involved, which is why all of this keeps working when the internet is down. The fan may well talk to the manufacturer's cloud on its own behalf — the app offers an account for remote access — but that happens without us.

The device id below is a placeholder. Yours is on a label under the front cover.

## The envelope

Every packet, in both directions, looks like this:

This is a real "start a boost" packet, 36 bytes, with the device id replaced by zeros:

```
FD FD 02 10 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 30 08 31 31 31 31 31 31 31 31 03 01 01 05 01 AD 04
└──┬──┘ │  │  └─────────────────────┬────────────────────────┘ │  └───────────┬──────────┘ │  └────┬────┘ └──┬──┘
   1    2  3                        4                          5              6            7       8         9
```

| # | Bytes | Meaning |
|---|-------|---------|
| 1 | `FD FD` | Start of packet. Always these two |
| 2 | `02` | Packet type. `02` is a normal command |
| 3 | `10` | Length of the device id that follows, 16 bytes |
| 4 | 16 bytes | The device id, as ascii digits |
| 5 | `08` | Length of the password that follows |
| 6 | 8 bytes | The password, as ascii. Factory default is `11111111` |
| 7 | `03` | Function. See below |
| 8 | 0 or more bytes | The payload: what you want to read or write |
| 9 | `B5 03` | Checksum, low byte first |

**The checksum** is the sum of every byte from #2 to #8 inclusive — everything except the two `FD` bytes and the checksum itself — kept to 16 bits and written low byte first.

**Functions** (byte #7):

| Value | Meaning |
|-------|---------|
| `01` | Read. The payload is a list of parameter numbers |
| `02` | Write, no answer |
| `03` | Write, and answer with the new state |
| `06` | The unit's answer. You receive this, you never send it |

## Reading

To ask for one parameter, the payload is just its number.

```
... 01 04 ...        function 01 = read, parameter 04 = fan speed
```

The answer carries the same envelope with function `06`, and a payload of parameter numbers followed by values:

```
04 ...  ->  FE 02 04 A0 05        FE = multi-byte value, 02 = two bytes,
                                  04 = the parameter, A0 05 = 1440 low byte first
01 ...  ->  01 01                 single byte: parameter 01, value 01
66 ...  ->  FD 66                 FD = this unit has no parameter 66
```

Three codes can appear in an answer before a parameter number: `FE` means the value takes several bytes, `FD` means the parameter does not exist on this unit, and `FF` changes the high byte for the parameter numbers that follow.

⛔ Ask for one parameter at a time. This unit stops answering if a single read asks for too many.

## Writing: start a boost

This is the whole packet. Nothing else is needed.

| Bytes | What it does | Verified |
|-------|--------------|----------|
| `01 01` | Power on | Yes. Without power, the next pair does nothing at all |
| `05 01` | Boost on | Yes. On its own, on a fan that already has power, this starts the boost |

The unit answers, beeps once, runs at its Max speed and starts counting down. The length of the boost is set in the app under Settings - Timers, not in this packet.

## Writing: stop a boost

| Bytes | What it does | Verified |
|-------|--------------|----------|
| `05 00` | Boost off | Yes. The countdown clears and the fan drops straight back to 24 hour mode, or to standing still if 24 hour mode is off |

Cutting power with `01 00` also ends a boost, but it stops the ventilation as well. Use `05 00`.

## What the bytes in the packets you find online actually do

Scripts in circulation, including the ones this repository shipped before 3 October 2026, send this to start a boost:

```
01 01 02 01 03 01 05 01 07 02 06 01 14 0F
```

Each pair was tested on its own and in combination. Only two of the seven matter:

| Bytes | What the old code believed | What it actually does |
|-------|---------------------------|----------------------|
| `01 01` | power on | **Power on. Needed** |
| `02 01` | speed 1 | Nothing observable. The parameter reads back 0 either way |
| `03 01` | ventilation mode | **Switches 24 hour mode on.** A setting the owner may have deliberately switched off, turned back on by every boost |
| `05 01` | aux | **The boost switch. This is the one that starts it** |
| `07 02` | boost mode | Nothing. `0x07` is a status value the unit sets itself, and it reads 1 while a boost runs no matter what you wrote |
| `06 01` | boost on | Nothing. `0x06` is the countdown, and the unit owns it |
| `14 0F` | boost duration, 15 minutes | **The humidity threshold in percent.** It accepts 40 to 80, so 15 is ignored — but `14 3C` would silently set the owner's humidity threshold to 60 on every press |

The lesson is not that the old packet was lazy. It is that writing to a status value looks exactly like success: the unit answers, the boost starts, and the byte that did the work is not the one you think.

## How this was established

Each pair was sent on its own from a known state, and the unit was read before and after. `05 01` alone started a boost. `07 02` alone, `06 01` alone, `02 01` alone and the full packet minus `05 01` all did nothing. The humidity threshold was identified by switching the humidity sensor to manual in the app, dragging the slider from 40 to 60 percent and watching `0x14` follow, then writing 40 back over the protocol and watching the slider follow.

Measured 3 October 2026 on unit type 6, firmware 2.1. `PROTOCOL.md` has the parameter table and the state model.
