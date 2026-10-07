# Hardware Identity

This document defines the coherence gates for nodes in this cluster.
The two gates are:
- `adc_ext_ref`: Host timestamp is supplemented by an external reference clock (EXT_REF_CLK) disciplining the ADC itself. Topdog is the only node currently in this class.
- `host_timestamp`: Node relies on the pipeline and PPS-disciplined host time. Nodes in this class are ravenpi and cm5-poe.
