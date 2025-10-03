from typing import TYPE_CHECKING, Union, Optional, TextIO, List, Tuple
import re

from systemrdl.node import AddrmapNode, SignalNode, FieldNode, RegNode, AddressableNode
from systemrdl.rdltypes import PropertyReference

from ..utils import get_indexed_path
from ..identifier_filter import kw_filter as kwf
from ..sv_int import SVInt

from .generators import InputStructGenerator_Hier, OutputStructGenerator_Hier
from .generators import InputStructGenerator_TypeScope, OutputStructGenerator_TypeScope
from .generators import EnumGenerator

if TYPE_CHECKING:
    from ..exporter import RegblockExporter, DesignState

class Hwif:
    """
    Defines how the hardware input/output signals are generated:
    - Field outputs
    - Field inputs
    - Signal inputs (except those that are promoted to the top)
    """

    def __init__(
        self, exp: 'RegblockExporter',
        hwif_report_file: Optional[TextIO]
    ):
        self.exp = exp

        self.has_input_struct = False
        self.has_output_struct = False

        self.hwif_report_file = hwif_report_file

        if not self.ds.reuse_hwif_typedefs:
            self._gen_in_cls = InputStructGenerator_Hier
            self._gen_out_cls = OutputStructGenerator_Hier
        else:
            self._gen_in_cls = InputStructGenerator_TypeScope
            self._gen_out_cls = OutputStructGenerator_TypeScope

    @property
    def ds(self) -> 'DesignState':
        return self.exp.ds

    @property
    def top_node(self) -> AddrmapNode:
        return self.exp.ds.top_node


    def get_extra_package_params(self) -> str:
        lines = [""]

        for param in self.top_node.inst.parameters:
            value = param.get_value()
            if isinstance(value, int):
                lines.append(
                    f"localparam {param.name} = {SVInt(value)};"
                )
            elif isinstance(value, str):
                lines.append(
                    f"localparam {param.name} = {value};"
                )

        return "\n".join(lines)


    def get_package_contents(self) -> str:
        """
        If this hwif requires a package, generate the string
        """
        lines = [""]

        gen_in = self._gen_in_cls(self)
        structs_in = gen_in.get_struct(
            self.top_node,
            f"{self.top_node.inst_name}__in_t"
        )
        if structs_in is not None:
            self.has_input_struct = True
            lines.append(structs_in)
        else:
            self.has_input_struct = False

        gen_out = self._gen_out_cls(self)
        structs_out = gen_out.get_struct(
            self.top_node,
            f"{self.top_node.inst_name}__out_t"
        )
        if structs_out is not None:
            self.has_output_struct = True
            lines.append(structs_out)
        else:
            self.has_output_struct = False

        gen_enum = EnumGenerator()
        enums = gen_enum.get_enums(self.ds.user_enums)
        if enums is not None:
            lines.append(enums)

        return "\n\n".join(lines)


    @property
    def port_declaration(self) -> str:
        """
        Returns the declaration string for all I/O ports in the hwif group
        """

        # Assume get_package_declaration() is always called prior to this
        assert self.has_input_struct is not None
        assert self.has_output_struct is not None

        lines = []
        if self.has_input_struct:
            type_name = f"{self.top_node.inst_name}__in_t"
            lines.append(f"input {self.ds.package_name}::{type_name} hwif_in")
        if self.has_output_struct:
            type_name = f"{self.top_node.inst_name}__out_t"
            lines.append(f"output {self.ds.package_name}::{type_name} hwif_out")

        return ",\n".join(lines)

    def _collect_flat_signals(self) -> Tuple[List[Tuple[str, str, int, int, List[Tuple[int, int]]]], List[Tuple[str, str, int, int, List[Tuple[int, int]]]]]:
        """
        Collect all flat signals from the hwif structs.
        Returns (input_signals, output_signals) where each signal is a tuple of
        (flattened_name, struct_path, width, lsb, array_dims)
        array_dims is a list of (msb, lsb) tuples for unpacked array dimensions
        """
        import io
        
        input_signals = []  # type: List[Tuple[str, str, int, int, List[Tuple[int, int]]]]
        output_signals = []  # type: List[Tuple[str, str, int, int, List[Tuple[int, int]]]]

        # Collect input signals using a temporary report
        if self.has_input_struct:
            temp_report = io.StringIO()
            temp_hwif = Hwif(self.exp, temp_report)
            temp_hwif.get_package_contents()
            
            # Parse the report
            temp_report.seek(0)
            for line in temp_report:
                line = line.strip()
                if line.startswith("hwif_in."):
                    input_signals.append(self._parse_signal_line(line, "hwif_in"))
        
        # Collect output signals using a temporary report
        if self.has_output_struct:
            temp_report = io.StringIO()
            temp_hwif = Hwif(self.exp, temp_report)
            temp_hwif.get_package_contents()
            
            # Parse the report
            temp_report.seek(0)
            for line in temp_report:
                line = line.strip()
                if line.startswith("hwif_out."):
                    output_signals.append(self._parse_signal_line(line, "hwif_out"))
        
        return input_signals, output_signals
    
    def _parse_signal_line(self, line: str, prefix: str) -> Tuple[str, str, int, int, List[Tuple[int, int]]]:
        """
        Parse a signal line from the hwif report.
        Format: hwif_in.path.to.signal[MSB:LSB]
        or:     hwif_in.path.to.signal
        Returns: (flattened_name, struct_path, width, lsb, array_dims)
        """
        # Extract bit range if present at the end
        width = 1
        lsb = 0
        path = line
        
        # Check if line ends with a bit range [MSB:LSB] or [BIT]
        match = re.search(r'\[(\d+)(?::(\d+))?\]$', line)
        if match:
            # Extract the path without the bit range
            path = line[:match.start()]
            
            if match.group(2):
                # Range [MSB:LSB]
                msb = int(match.group(1))
                lsb = int(match.group(2))
                width = msb - lsb + 1
            else:
                # Single bit [BIT]
                lsb = int(match.group(1))
                width = 1
        
        # Extract array dimensions from the path
        array_dims = []  # type: List[Tuple[int, int]]
        temp_path = path
        
        # Find all array ranges in the path (e.g., [0:63])
        for match in re.finditer(r'\[(\d+):(\d+)\]', temp_path):
            msb = int(match.group(1))
            lsb_idx = int(match.group(2))
            array_dims.append((msb, lsb_idx))
        
        # Convert path to flat name (remove array dimensions)
        flat_name = path.replace(f"{prefix}.", "")
        # Remove array ranges from the flat name
        flat_name = re.sub(r'\[(\d+):(\d+)\]', '', flat_name)  # Remove [0:63]
        flat_name = re.sub(r'\[(\d+)\]', r'_\1', flat_name)  # Convert single [0] to _0
        flat_name = flat_name.replace(".", "_")
        
        return (flat_name, path, width, lsb, array_dims)

    def get_flat_port_declarations(self) -> str:
        """
        Generate flat port declarations for the wrapper module.
        """
        if not self.has_input_struct and not self.has_output_struct:
            return ""
        
        lines = []
        input_signals, output_signals = self._collect_flat_signals()
        
        for flat_name, _, width, lsb, array_dims in input_signals:
            # Remove "_next" suffix from port name if present
            port_name = flat_name[:-5] if flat_name.endswith("_next") else flat_name
            
            # Remove redundant names (e.g., x_x becomes x)
            parts = port_name.split('_')
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                port_name = '_'.join(parts[:-1])
            
            # Build unpacked dimensions (array indices)
            # Use [N-1:0] syntax for unpacked arrays
            # Note: Dimensions must be in REVERSE order for port declarations
            unpacked_dims = ""
            for first, last in reversed(array_dims):
                # Calculate size (number of elements)
                size = abs(first - last) + 1
                unpacked_dims += f"[{size-1}:0] "
            
            # Build packed dimension (bit range)
            if width == 1 and lsb == 0:
                packed_dim = ""
            else:
                packed_dim = f"[{lsb+width-1}:{lsb}] "
            
            lines.append(f"input logic {unpacked_dims}{packed_dim}hwif_in_{port_name}")
        
        for flat_name, _, width, lsb, array_dims in output_signals:
            # Remove "_value" or "_next" suffix from port name if present
            if flat_name.endswith("_value"):
                port_name = flat_name[:-6]
            elif flat_name.endswith("_next"):
                port_name = flat_name[:-5]
            else:
                port_name = flat_name
            
            # Remove redundant names (e.g., x_x becomes x)
            parts = port_name.split('_')
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                port_name = '_'.join(parts[:-1])
            
            # Build unpacked dimensions (array indices)
            # Use [N-1:0] syntax for unpacked arrays
            # Note: Dimensions must be in REVERSE order for port declarations
            unpacked_dims = ""
            for first, last in reversed(array_dims):
                # Calculate size (number of elements)
                size = abs(first - last) + 1
                unpacked_dims += f"[{size-1}:0] "
            
            # Build packed dimension (bit range)
            if width == 1 and lsb == 0:
                packed_dim = ""
            else:
                packed_dim = f"[{lsb+width-1}:{lsb}] "
            
            lines.append(f"output logic {unpacked_dims}{packed_dim}hwif_out_{port_name}")
        
        return ",\n".join(lines)

    def get_flat_signal_assignments(self) -> str:
        """
        Generate assignments between flat signals and struct members.
        """
        if not self.has_input_struct and not self.has_output_struct:
            return ""
        
        lines = []
        input_signals, output_signals = self._collect_flat_signals()
        
        # Input assignments: flat signal -> struct
        for flat_name, struct_path, _, _, array_dims in input_signals:
            # Remove "_next" suffix from port name if present
            port_name = flat_name[:-5] if flat_name.endswith("_next") else flat_name
            
            # Remove redundant names (e.g., x_x becomes x)
            parts = port_name.split('_')
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                port_name = '_'.join(parts[:-1])
            
            if array_dims:
                # Has arrays - need to generate per-element assignments
                lines.extend(self._generate_array_assignments(
                    f"hwif_in_{port_name}", struct_path, array_dims, is_input=True
                ))
            else:
                # No arrays - simple assignment
                lines.append(f"assign {struct_path} = hwif_in_{port_name};")
        
        # Output assignments: struct -> flat signal  
        for flat_name, struct_path, _, _, array_dims in output_signals:
            # Remove "_value" or "_next" suffix from port name if present
            if flat_name.endswith("_value"):
                port_name = flat_name[:-6]
            elif flat_name.endswith("_next"):
                port_name = flat_name[:-5]
            else:
                port_name = flat_name
            
            # Remove redundant names (e.g., x_x becomes x)
            parts = port_name.split('_')
            if len(parts) >= 2 and parts[-1] == parts[-2]:
                port_name = '_'.join(parts[:-1])
            
            if array_dims:
                # Has arrays - need to generate per-element assignments
                lines.extend(self._generate_array_assignments(
                    f"hwif_out_{port_name}", struct_path, array_dims, is_input=False
                ))
            else:
                # No arrays - simple assignment
                lines.append(f"assign hwif_out_{port_name} = {struct_path};")
        
        return "\n".join(lines)
    
    def _generate_array_assignments(self, port_name: str, struct_path: str, array_dims: List[Tuple[int, int]], is_input: bool) -> List[str]:
        """
        Generate element-by-element assignments for arrays using generate loops.
        """
        lines = []
        
        # Build index variable names (i, j, k, ...)
        index_vars = []
        for idx in range(len(array_dims)):
            index_vars.append(chr(ord('i') + idx))
        
        # Start generate block
        lines.append("generate")
        
        # Create nested for loops
        for idx, (first, last, var) in enumerate(zip([d[0] for d in array_dims], [d[1] for d in array_dims], index_vars)):
            size = abs(first - last)
            indent = "    " * (idx + 1)
            lines.append(f"{indent}for (genvar {var} = 0; {var} <= {size}; {var}++) begin")
        
        # Generate the assignment
        indent = "    " * (len(array_dims) + 1)
        
        # Build array indices for the flat port side
        # Note: Indices must be in REVERSE order to match reversed declaration order
        array_indices = "".join([f"[{var}]" for var in reversed(index_vars)])
        
        # For the struct path, replace each [N:M] range with the corresponding index variable
        # Process the path to replace array ranges with individual indices
        clean_struct_path = struct_path
        idx_counter = 0
        
        # Replace each [N:M] pattern with the corresponding index variable [i], [j], etc.
        def replace_with_index(match):
            nonlocal idx_counter
            if idx_counter < len(index_vars):
                result = f"[{index_vars[idx_counter]}]"
                idx_counter += 1
                return result
            return match.group(0)
        
        clean_struct_path = re.sub(r'\[(\d+):(\d+)\]', replace_with_index, clean_struct_path)
        
        if is_input:
            lines.append(f"{indent}assign {clean_struct_path} = {port_name}{array_indices};")
        else:
            lines.append(f"{indent}assign {port_name}{array_indices} = {clean_struct_path};")
        
        # Close generate loops
        for idx in range(len(array_dims) - 1, -1, -1):
            indent = "    " * (idx + 1)
            lines.append(f"{indent}end")
        
        lines.append("endgenerate")
        
        return lines

    #---------------------------------------------------------------------------
    # hwif utility functions
    #---------------------------------------------------------------------------
    def has_value_input(self, obj: Union[FieldNode, SignalNode]) -> bool:
        """
        Returns True if the object infers an input wire in the hwif
        """
        if isinstance(obj, FieldNode):
            return obj.is_hw_writable
        elif isinstance(obj, SignalNode):
            # Signals are implicitly always inputs
            return True
        else:
            raise RuntimeError


    def has_value_output(self, obj: FieldNode) -> bool:
        """
        Returns True if the object infers an output wire in the hwif
        """
        return obj.is_hw_readable


    def get_input_identifier(
        self,
        obj: Union[FieldNode, SignalNode, PropertyReference],
        width: Optional[int] = None,
    ) -> Union[SVInt, str]:
        """
        Returns the identifier string that best represents the input object.

        if obj is:
            Field: the fields hw input value port
            Signal: signal input value
            Prop reference:
                could be an implied hwclr/hwset/swwe/swwel/we/wel input

        raises an exception if obj is invalid
        """
        if isinstance(obj, FieldNode):
            next_value = obj.get_property('next')
            if next_value is not None:
                # 'next' property replaces the inferred input signal
                return self.exp.dereferencer.get_value(next_value, width)
            # Otherwise, use inferred
            path = get_indexed_path(self.top_node, obj)
            return "hwif_in." + path + ".next"
        elif isinstance(obj, SignalNode):
            if obj.get_path() in self.ds.out_of_hier_signals:
                return kwf(obj.inst_name)
            path = get_indexed_path(self.top_node, obj)
            return "hwif_in." + path
        elif isinstance(obj, PropertyReference):
            assert isinstance(obj.node, FieldNode)
            return self.get_implied_prop_input_identifier(obj.node, obj.name)

        raise RuntimeError(f"Unhandled reference to: {obj}")

    def get_external_rd_data(self, node: AddressableNode) -> str:
        """
        Returns the identifier string for an external component's rd_data signal
        """
        path = get_indexed_path(self.top_node, node)
        return "hwif_in." + path + ".rd_data"

    def get_external_rd_ack(self, node: AddressableNode) -> str:
        """
        Returns the identifier string for an external component's rd_ack signal
        """
        path = get_indexed_path(self.top_node, node)
        return "hwif_in." + path + ".rd_ack"

    def get_external_wr_ack(self, node: AddressableNode) -> str:
        """
        Returns the identifier string for an external component's wr_ack signal
        """
        path = get_indexed_path(self.top_node, node)
        return "hwif_in." + path + ".wr_ack"

    def get_implied_prop_input_identifier(self, field: FieldNode, prop: str) -> str:
        assert prop in {
            'hwclr', 'hwset', 'swwe', 'swwel', 'we', 'wel',
            'incr', 'decr', 'incrvalue', 'decrvalue'
        }
        path = get_indexed_path(self.top_node, field)
        return "hwif_in." + path + "." + prop


    def get_output_identifier(self, obj: Union[FieldNode, PropertyReference]) -> str:
        """
        Returns the identifier string that best represents the output object.

        if obj is:
            Field: the fields hw output value port
            Property ref: this is also part of the struct

        raises an exception if obj is invalid
        """
        if isinstance(obj, FieldNode):
            path = get_indexed_path(self.top_node, obj)
            return "hwif_out." + path + ".value"
        elif isinstance(obj, PropertyReference):
            # TODO: this might be dead code.
            # not sure when anything would call this function with a prop ref
            # when dereferencer's get_value is more useful here
            assert obj.node.get_property(obj.name)
            assert isinstance(obj.node, (RegNode, FieldNode))
            return self.get_implied_prop_output_identifier(obj.node, obj.name)

        raise RuntimeError(f"Unhandled reference to: {obj}")


    def get_implied_prop_output_identifier(self, node: Union[FieldNode, RegNode], prop: str) -> str:
        if isinstance(node, FieldNode):
            assert prop in {
                "anded", "ored", "xored", "swmod", "swacc",
                "incrthreshold", "decrthreshold", "overflow", "underflow",
                "rd_swacc", "wr_swacc",
            }
        elif isinstance(node, RegNode):
            assert prop in {
                "intr", "halt",
            }
        path = get_indexed_path(self.top_node, node)
        return "hwif_out." + path + "." + prop
