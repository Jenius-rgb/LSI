# Board bring-up plan (ZERO7)

Only start this when `board/BOARD_INFO.md` has no `UNKNOWN` in its required fields and the
user has confirmed the board is in hand (CLAUDE.md section 8). Do not change any voltage.
Always start at the safe clock. Overclocking comes only after E7 is bit-exact at the safe clock.

Each step is one subcommand of `board/bringup.py`. Steps 1 and 2 run on the PC, the rest on the
Raspberry Pi. Every step can be rehearsed on a PC with `--dry-run`, which uses the Python model
of the device and proves nothing about hardware. Save the output of each step under
`results/hw/bringup/` and label it `[HW]`.

| Step | Command | Pass criterion | If it fails |
| --- | --- | --- | --- |
| 1. Power | `python board/bringup.py power` | The checklist in the script is confirmed by hand; voltages read with a meter | Stop. Check the power source and the board documentation |
| 2. Programming | `python board/bringup.py program` | Vivado Hardware Manager (or the method documented for ZERO7) programs the bitstream; DONE indicator, if the board has one | Check cable and part number in BOARD_INFO |
| 3. LED blink | `python board/bringup.py led` | LED1 to LED4 follow the pattern from the bitstream | Check XDC pin assignment |
| 4. SPI loopback | `python board/bringup.py spi-loopback` | A pattern written to a scratch register reads back identically at the lowest SPI speed | Check SPI pins, mode, CS polarity, level voltage |
| 5. Read ID | `python board/bringup.py id` | Returns `SNTL` and the expected version and K | Check the bitstream build |
| 6. Load weights | `python board/bringup.py load --model s` | Read-back of the first 256 weight bytes matches the file | Lower the SPI speed |
| 7. One image | `python board/bringup.py one-image` | Class and logits match the golden model | Stop. Do not raise the clock |
| 8. Full validation at the safe clock | `python board/bringup.py validate --images 200` | 100% logits match (this is E7) | Stop. Do not raise the clock |
| 9. Turbo, one step at a time | `python board/bringup.py turbo` | Only after step 8. Raises the turbo level step by step and reports `[HW]` counters; stops at the first FATAL | Lower the level, re-run E7 at the safe clock |

Facts this plan needs but does not assume are listed in `board/BOARD_INFO.md`. The script stops
with a message if a required field is still `UNKNOWN`.
