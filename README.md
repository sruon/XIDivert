# XIDivert

Patches retail VTABLE.DAT/FTABLE.DAT to inject "era" DATs at custom paths.
Allows executing older events in any zone without replacing the zone events and strings tables and having to work around updates to the retail client.

## How It Works

When the client receives an event from the server, it compares `EventNum` with `EventNum2`. 
They are usually both set to the current zone ID, except in Aht Urghan Whitegate where `EventNum2` may be set to 0.

If `EventNum2` doesn't match `EventNum`, the client shifts its DAT lookup for events and messages by +1000 and loads the events and strings using the new index.
This index is then used to read the ROM folder in `VTABLE.DAT`, and then the actual target files from `FTABLE.DAT`.

By passing a custom "text_table" (a misnomer really) server-side, you can force the client to load data for an event from an alternate location.
```
-- Before
player:startEvent(310, menu, arg3, arg4, gil, cosmoTime, 1, hasCosmoCleanse, storedABCs)

-- After
player:startEvent(310, menu, arg3, arg4, gil, cosmoTime, 1, hasCosmoCleanse, storedABCs, 400)
```

This repository takes a set of swaps, copies retail FTABLE/VTABLE and find holes where the new references can be introduced. 
It then generates a complete layout that can be shipped to users.

## Quick Start

- Add extra swaps to the folder - ensure each folder contains both `events.DAT` and `strings.DAT`
  - Sourcing the `.DATs` is your own problem, the ones in this repository are merely here for demonstration.
- Add a new entry to `manifest.yaml` for each swap
- Execute `xidivert.py`
- Ship content of `output` folder
- Update server-side events to use the new indices

```bash
python xidivert.py

Loading manifest: C:\Users\sruon\Documents\GitHub\XIDivert\manifest.yaml
FFXI: C:\Program Files (x86)\PlayOnline\SquareEnix\FINAL FANTASY XI
ROM folder: ROM255/
Swaps: 2

Processing swaps:
  port_jeuno_2009 -> text_table=400 (1 entity replacements)
  rulude_2009 -> text_table=401

Generated: C:\Users\sruon\Documents\GitHub\XIDivert\output\divert.lua

Done! Copy output/ contents to your FFXI installation.
```

The generated lua can be used server-side

```lua
xi.divert =
{
    PORT_JEUNO_2009 = 400,
    RULUDE_2009 = 401,
}
```

## Handling NPC shifts
Old ID (referenced in event) -> current retail ID

See [FFXI-EventsDump](https://github.com/sruon/FFXI-EventsDump) for code to parse the events and figure out the original NPC IDs.

Note: If the NPC has not shifted or is not strictly referenced in the event, it may not be necessary.
```yaml
swaps:
  - name: "Port Jeuno (2009)"
    path: "port_jeuno_2009"
    description: "Port Jeuno events from Ultimate Collection (2009~). Sagheera 15k Cosmo-Cleanse, Conquest NPC"
    entity_ids:
      17784952: 17784962 # Sagheera
```

## Limitations
- Does not handle japanese strings
- DAT format may have changed over the year, which will lead to crashes.
- Must repatch the tables after every retail update

## Support
None whatsoever, you're on your own.

## Credits
- atom0s for [XiEvents](https://github.com/atom0s/XiEvents/tree/main)
