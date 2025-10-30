{% extends "lib/tb_base.sv" %}

{%- block declarations %}
    {% sv_line_anchor %}
    localparam REGWIDTH = {{testcase.regwidth}};
    localparam STRIDE = REGWIDTH/8;
{%- endblock %}


{% block seq %}
    {% sv_line_anchor %}
    bit [REGWIDTH-1:0] data0;
    bit [REGWIDTH-1:0] data1;
    bit [REGWIDTH-1:0] data2;

    ##1;
    cb.rst <= '0;
    ##1;

    // Read initial value from register at address 0x0
    cpuif.assert_read(0, 'h1);
    cpuif.assert_read(8, 'h1);

    // Write random data to register at address 0x0
    data0 = 'haba556beb1789acb;
    data1 = 'hb1dfb4d795386519;
    data2 = 'ha1b38524244b020b;

    cpuif.write(0, data0);
    cpuif.write(8, data1);

    // Read back and verify the written data
    cpuif.assert_read(0, data0);
    cpuif.assert_read(8, data1);

    cpuif.write(4, data2);
    cpuif.assert_read(0, data2);

{% endblock %}

