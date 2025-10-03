"""
HWIF Report Parser
Parses hwif report files to extract signal information
"""
import re
from typing import List, Tuple


class HwifSignal:
    """Represents a single hwif signal"""
    
    def __init__(self, struct_path: str, width: int, lsb: int, array_dims: List[Tuple[int, int]]):
        self.struct_path = struct_path
        self.width = width
        self.lsb = lsb
        self.array_dims = array_dims  # List of (msb, lsb) tuples for each array dimension
        
        # Determine direction from struct_path
        if struct_path.startswith("hwif_in."):
            self.direction = "input"
            self.prefix = "hwif_in"
        elif struct_path.startswith("hwif_out."):
            self.direction = "output"
            self.prefix = "hwif_out"
        else:
            raise ValueError(f"Unknown hwif prefix in: {struct_path}")
        
        # Generate flat name
        self.flat_name = self._generate_flat_name()
        self.port_name = self._generate_port_name()
    
    def _generate_flat_name(self) -> str:
        """Generate flattened signal name from struct path"""
        # Remove prefix
        name = self.struct_path.replace(f"{self.prefix}.", "")
        
        # Remove array ranges [N:M] including negative indices (Q format fields)
        name = re.sub(r'\[(-?\d+):(-?\d+)\]', '', name)
        
        # Convert single indices [N] to _N (use abs() for negative indices)
        name = re.sub(r'\[(-?\d+)\]', lambda m: f"_{abs(int(m.group(1)))}", name)
        
        # Replace dots with underscores
        name = name.replace(".", "_")
        
        return name
    
    def _generate_port_name(self) -> str:
        """Generate port name with suffix removal ONLY if struct path ends with .next or .value"""
        name = self.flat_name
        
        # Only remove suffix if the struct path actually ends with .next or .value
        # (not if it's part of the field name like f_next_value)
        
        # Check if struct path (without bit range) ends with .next
        path_no_bitrange = re.sub(r'\[\d+(?::\d+)?\]$', '', self.struct_path)
        
        if path_no_bitrange.endswith(".next"):
            # Remove _next suffix from flat name
            if name.endswith("_next"):
                name = name[:-5]
        elif path_no_bitrange.endswith(".value"):
            # Remove _value suffix from flat name
            if name.endswith("_value"):
                name = name[:-6]
        
        # Remove redundant names (e.g., x_x becomes x)
        parts = name.split('_')
        if len(parts) >= 2 and parts[-1] == parts[-2]:
            name = '_'.join(parts[:-1])
        
        return name
    
    def get_port_declaration(self) -> str:
        """Generate port declaration string"""
        # Build unpacked dimensions (arrays) - in REVERSE order
        unpacked_dims = ""
        for first, last in reversed(self.array_dims):
            size = abs(first - last) + 1
            unpacked_dims += f"[{size-1}:0] "
        
        # Build packed dimension (bit width)
        if self.width == 1 and self.lsb == 0:
            packed_dim = ""
        else:
            packed_dim = f"[{self.lsb + self.width - 1}:{self.lsb}] "
        
        # Format: <direction> logic [unpacked...] [packed] <name>
        return f"{self.direction} logic {unpacked_dims}{packed_dim}{self.prefix}_{self.port_name}"


def parse_hwif_report(report_path: str) -> Tuple[List[HwifSignal], List[HwifSignal]]:
    """
    Parse an hwif report file and return input and output signals
    
    Returns:
        (input_signals, output_signals)
    """
    input_signals = []
    output_signals = []
    
    with open(report_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            signal = parse_signal_line(line)
            
            if signal.direction == "input":
                input_signals.append(signal)
            else:
                output_signals.append(signal)
    
    return input_signals, output_signals


def parse_signal_line(line: str) -> HwifSignal:
    """
    Parse a single line from hwif report
    
    Format: hwif_in.path.to.signal[MSB:LSB]
    or:     hwif_in.path.to.signal
    
    Returns HwifSignal object
    """
    # Extract bit range if present at the end (handle negative indices for Q format)
    width = 1
    lsb = 0
    path = line
    
    # Check if line ends with a bit range [MSB:LSB] or [BIT] (including negative numbers)
    match = re.search(r'\[(-?\d+)(?::(-?\d+))?\]$', line)
    if match:
        # Extract the path without the bit range
        path = line[:match.start()]
        
        if match.group(2):
            # Range [MSB:LSB] - can have negative values for Q format fields
            msb = int(match.group(1))
            lsb_val = int(match.group(2))
            width = abs(msb - lsb_val) + 1
            # For port declarations, Q format fields always start at bit 0
            lsb = 0
        else:
            # Single bit [BIT] - can be negative
            # Single bit ports are always [0:0]
            lsb = 0
            width = 1
    
    # Extract array dimensions from the path
    array_dims = []
    
    # Find all array ranges in the path (e.g., [0:63])
    # Array dimensions should only have positive indices
    for match in re.finditer(r'\[(\d+):(\d+)\]', path):
        msb = int(match.group(1))
        lsb_idx = int(match.group(2))
        array_dims.append((msb, lsb_idx))
    
    return HwifSignal(path, width, lsb, array_dims)
