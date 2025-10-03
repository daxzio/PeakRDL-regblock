# HWIF Wrapper Tool - Overview

## What Is This?

A **standalone Python package** in the `/hwif_wrapper_tool/` directory that generates hwif wrapper modules **without modifying PeakRDL-regblock source code**.

## Quick Links

📍 **Start Here**: [hwif_wrapper_tool/INDEX.md](hwif_wrapper_tool/INDEX.md)

⚡ **Quick Start**: [hwif_wrapper_tool/QUICK_START.md](hwif_wrapper_tool/QUICK_START.md)

✅ **Verification**: [hwif_wrapper_tool/VERIFICATION.md](hwif_wrapper_tool/VERIFICATION.md)

📘 **Full Summary**: [hwif_wrapper_tool/FINAL_SUMMARY.md](hwif_wrapper_tool/FINAL_SUMMARY.md)

## The Problem It Solves

PeakRDL-regblock generates modules with **hierarchical struct** hwif ports:
```systemverilog
input  regblock_pkg::regblock__in_t  hwif_in;   // Struct
output regblock_pkg::regblock__out_t hwif_out;  // Struct
```

Some tools/workflows prefer **flat individual signals**:
```systemverilog
input  logic [7:0] hwif_in_reg_field;   // Flat
output logic [7:0] hwif_out_reg_data;   // Flat
```

## The Solution

This tool generates a **wrapper module** that:
1. Presents flat signals at the top level
2. Internally creates the struct signals
3. Connects flat ↔ struct with assignments
4. Instantiates the main regblock module

## Usage (No Installation Required!)

### Option 1: Run Script Directly

**Simplest approach** - just run the script:

```bash
cd hwif_wrapper_tool
source ../venv/bin/activate

python3 generate_wrapper.py design.rdl -o output/
```

**Requirements**: Just need `peakrdl-regblock` installed (already in venv)

### Option 2: Install as Package (Optional)

```bash
cd hwif_wrapper_tool
source ../venv/bin/activate
pip install -e .

# Then use as command
peakrdl-hwif-wrapper design.rdl -o output/
```

Generates:
- `module_pkg.sv` - Package (from PeakRDL-regblock)
- `module.sv` - Main module (from PeakRDL-regblock)
- `module_wrapper.sv` - **Wrapper with flat ports** ← NEW!

## Features

- ✅ No PeakRDL-regblock modifications required
- ✅ Removes `_next` and `_value` suffixes
- ✅ Handles single and multi-dimensional arrays
- ✅ Generates SystemVerilog generate loops
- ✅ Works with all CPU interface types
- ✅ Verilator compatible
- ✅ **Verified equivalent** to integrated version

## Verification Status

**Tested Against**: Integrated version (hwif_wrapper branch)

**Result**: ✅ **Functionally IDENTICAL**
- 4/4 comparison tests: Identical output
- 26/26 cocotb tests: All pass
- 3/3 Verilator tests: All pass

See [hwif_wrapper_tool/VERIFICATION.md](hwif_wrapper_tool/VERIFICATION.md) for details.

## Documentation

**11 documentation files, ~2,000 lines**:

### Quick Reference
- [INDEX.md](hwif_wrapper_tool/INDEX.md) - Documentation navigator
- [QUICK_START.md](hwif_wrapper_tool/QUICK_START.md) - Get started in 5 min
- [USAGE.md](hwif_wrapper_tool/USAGE.md) - Complete guide

### Technical
- [IMPLEMENTATION_SUMMARY.md](hwif_wrapper_tool/IMPLEMENTATION_SUMMARY.md) - How it works
- [VERIFICATION.md](hwif_wrapper_tool/VERIFICATION.md) - Test results
- [FINAL_SUMMARY.md](hwif_wrapper_tool/FINAL_SUMMARY.md) - Complete summary

### Specification
- [HWIF_WRAPPER_REQUIREMENTS.md](HWIF_WRAPPER_REQUIREMENTS.md) - Full spec

## Example

```bash
$ peakrdl-hwif-wrapper design.rdl -o output/
Generated files in output/:
  - module_pkg.sv
  - module.sv
  - module_wrapper.sv
✅ Wrapper generation complete!
```

## Code Structure

```
hwif_wrapper_tool/
├── hwif_wrapper_tool/      # Python package (560 lines)
│   ├── __init__.py         # Package exports
│   ├── cli.py              # CLI interface
│   ├── generator.py        # Main orchestrator
│   ├── parser.py           # Report parser
│   ├── template_generator.py  # Assignment generator
│   └── wrapper_builder.py  # Wrapper builder
├── pyproject.toml          # Package config
├── *.md                    # Documentation (11 files)
├── example.py              # Usage examples
├── test_standalone.sh      # Test script
└── verify_equivalence.sh   # Verification script
```

## Why Standalone?

### Advantages

1. **No modification required**: Works with stock PeakRDL-regblock
2. **Independent updates**: Update wrapper logic without touching main codebase
3. **Easy customization**: Modify for your specific needs
4. **Version independent**: Works with any PeakRDL-regblock version
5. **Separate distribution**: Can distribute independently

### Comparison with Integrated

| Aspect | Standalone | Integrated |
|--------|-----------|------------|
| Source mods | **None** | Requires changes |
| Installation | `pip install -e hwif_wrapper_tool` | Included |
| Usage | `peakrdl-hwif-wrapper ...` | `peakrdl regblock ... --hwif-wrapper` |
| Output | **Identical** | **Identical** |
| Maintenance | Independent | Coupled |

## Status

**Phase**: ✅ Complete and Verified

**Quality**:
- ✅ Production ready
- ✅ Fully tested
- ✅ Well documented
- ✅ Verified equivalent

## Get Started

1. **Install**: `cd hwif_wrapper_tool && pip install -e .`
2. **Quick test**: `./test_standalone.sh`
3. **Use**: `peakrdl-hwif-wrapper design.rdl -o output/`
4. **Learn more**: See [hwif_wrapper_tool/INDEX.md](hwif_wrapper_tool/INDEX.md)

---

**Questions?** Start with [hwif_wrapper_tool/QUICK_START.md](hwif_wrapper_tool/QUICK_START.md)

**Need details?** See [hwif_wrapper_tool/INDEX.md](hwif_wrapper_tool/INDEX.md)

**Verification?** Read [hwif_wrapper_tool/VERIFICATION.md](hwif_wrapper_tool/VERIFICATION.md)

