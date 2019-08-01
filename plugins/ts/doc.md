# program_association_section

The Program Association Table provides the correspondence between a program_number and the PID value of the Transport Stream packets which carry the program definition. The program_number is the numeric label associated with a program.

## table_id

The table_id field identifies the content of a Transport Stream PSI section as shown in table 2-27 below.

| value     | description                                  |
| :-------- | :------------------------------------------- |
| 0x00      | program_association_section                  |
| 0x01      | conditional_access_section(CA_section)       |
| 0x02      | TS_program_map_section                       |
| 0x03-0x3F | ITU-T Rec. H.222.0 \| ISO/IEC 13818 reserved |
| 0x40-0xFE | User private                                 |
| 0xFF      | forbidden                                    |