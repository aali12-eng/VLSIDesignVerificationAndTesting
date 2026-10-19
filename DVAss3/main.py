from re import search
import re

# Read the Verilog source file into a string for parsing.
#please chnge the input file name if the file name is different
input_file_name="c432_new.v";

print("Input file name:"+input_file_name)
file =open(input_file_name, "r");
content= file.read();
# List the standard-cell gate types to find in the Verilog source.
gates_keyword={"AND2X1", "OR2X1", "NAND2X1", "NOR2X1", "XOR2X1", "INVX1", "BUFX1","XOR2X1"};

# Define which gate fault indexes are retained after applying the equivalence rules.
fault_should_remain_rules={"AND2X1":"1345", "OR2X1":"0245", "NAND2X1":"1345", "NOR2X1":"0245", "XOR2X1":"012345", "INVX1":"01", "BUFX1":"01"};

#single statement is individual statement of a gate in the verilog file. For example, "AND2X1 U1 ( .A(a), .B(b), .Y(c) );" is a single statement of AND2X1 gate.
single_statements=[]

#gate_ios_list is a list of tuples where each tuple contains the gate name, input1, input2 and output of a gate. For example, ("AND2X1", "a", "b", "c") is a tuple for AND2X1 gate with input1 as "a", input2 as "b" and output as "c".
gate_ios_list={}

#all_faults stores the faults 
input_output_faults=[]

# Extract the module name for use in the output filenames.
module_name = re.search(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_$]*)", content).group(1)


# Find the module's input declarations and split them into individual port names.
input_pattern = r"(?m)^\s*input\s+([^;]+);"
input_ports = [port.strip() for ports in re.findall(input_pattern, content) for port in ports.split(",")]


matches = []

# Build a pattern for each supported gate and capture its output and input signals.
for gate in gates_keyword:
    gate_pattern = (
        rf"\b{re.escape(gate)}\s+[A-Za-z_$][A-Za-z0-9_$]*\s*"
        r"\(\s*\.Y\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)\s*,"
        r"\s*\.A\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\)"
        r"(?:\s*,\s*\.B\s*\(\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*\))?"
        r"\s*\)\s*;"
    )
    
    for match in re.finditer(gate_pattern, content):
        output, input1, input2 = match.groups()
        matches.append(
            (match.start(), (gate, input1, input2, output))
        )


gate_ios_list = [item for _, item in sorted(matches)]



input_fanouts = []
input_fanout_faults = {}
port_fanout_count = {}
total_ios_fanout_count = 0
#check fi there is any fanout of the input ports, if there are fanouts then keep the the stem's stuck at faults but ignore the fanouts currently because they are being considered with gate inputs
for gate, input1,  input2, _ in gate_ios_list:
    for port in input_ports:
        if(port==input1 or port== input2):
            port_fanout_count[port] = port_fanout_count.get(port, 0) + 1
            if port_fanout_count.get(port) >1:
                input_fanout_faults[port+"_basic"] = {f"{port}in_sa0", f"{port}in_sa1"}
        



#Removing the faults from the ouput of any two input gate output which is the inoput of the second gate
for i, (gate, input1,  input2, output) in enumerate(gate_ios_list):
    k=0
    # Initialize counters and storage for input-port fanout faults.
    for j, (other_gate, other_input1,  other_input2, other_output) in enumerate(gate_ios_list):
        if i != j and output in (other_input1, other_input2):
            k+=1
        if(k>=2):
            gate_ios_list[i] = (gate, input1,  input2, output)
            break;
        elif(k<=1) & (i< len(gate_ios_list)-1):
            gate_ios_list[i] = (gate, input1,  input2, None)
        else:
            gate_ios_list[i] = (gate, input1,  input2, output)

#Removing the faults from the ouput of any one input gate such as INX/Buf output which is the input of the second gate
for i, (gate, input1,  input2, output) in enumerate(gate_ios_list):
    k=0
    if gate in {"INVX1", "BUFX1"} and (i + 1 < len(gate_ios_list)):
        for j, (other_gate, other_input1,  other_input2, other_output) in enumerate(gate_ios_list):
            if i != j and output in (other_input1, other_input2):
                k+=1
            next_gate = gate_ios_list[i + 1]
            if(next_gate in {"INVX1", "BUFX1"}):
                gate_ios_list[i] = (gate, None,  None, None)
            else: 
                if(k>=2):
                    gate_ios_list[i] = (gate, None,  None, output) #If there is branch then keep the sa0 and sa1 at the ouput of the INV/Buf
                    break;
                elif(k==1) & (i< len(gate_ios_list)-1):
                    gate_ios_list[i] = (gate, None,  None, None) #If back to back connected with the another gate then remove from input and ouput INV/Buf
                else:
                    gate_ios_list[i] = (gate, None,  None, output)

total_no_of_faults=len(gate_ios_list)
faults_by_gate = []
sa_faults_list=[]
#creating sa0 and sa1 for each lines
for gate, input1,  input2, output in gate_ios_list:
    gate_faults = []
    for signal in (input1, input2, output):
        if(signal is not None):
            gate_faults.extend((f"{signal}_sa0", f"{signal}_sa1"))
            sa_faults_list.extend([f"sa0 {signal}", f"sa1 {signal}"])
        else:
            gate_faults.extend((f"", f""))
    faults_by_gate.append({gate:gate_faults})

new_processed_list = [input_fanout_faults]
remaining_faults = []

#applying the fault equivalent rules and reducing the faults which are equvailent to the output faults
for fig in faults_by_gate:
    for key, value in fig.items():
        if key in fault_should_remain_rules:
            equivalent_rule = fault_should_remain_rules[key]
            remaining_faults=[]
            indexes = [int(char) for char in equivalent_rule]
            for index in indexes:
                if value[index]:
                    remaining_faults.append(value[index])
            fig[key] = remaining_faults
            new_processed_list.append(fig)  

#Adding the remaining faults in the circuit and the basic input fanout faults
total_remaining_faults = sum( 
    len(faults)
    for gate_fault in new_processed_list
    for faults in gate_fault.values()
)

# Writing the faults before collapsing to the text file
fault_signals = list(dict.fromkeys(
    signal
    for _, input1, input2, output in gate_ios_list
    for signal in (input1, input2, output)
    if signal is not None
))

total_faults_before_collapsing = len(sa_faults_list)
with open(module_name + "_BF.txt", "w") as file:
    for fault in sa_faults_list:
        file.write(f"{fault}\n")
    file.write(f"\nTotal Faults_BF = {total_faults_before_collapsing}\n")

# Writing the remaining faults to a text file
with open("faults_after_equivalence.txt", "w") as file:
    file.write("Remaining faults by gate:\n")
    for gate_fault in new_processed_list:
        for gate, faults in gate_fault.items():
            file.write(f"{gate}: {', '.join(faults)}\n")
    file.write(f"\nTotal remaining faults: {total_remaining_faults}\n")


189	# Store the unique collapsed faults; use seen to avoid counting duplicates.
collapsed_faults = []
seen = set()
# Walk through each fault group and collect each non-empty fault only once.
# Collect the unique faults to list before the equivalent classes.
for fault_group in new_processed_list:
    for faults in fault_group.values():
        for fault in faults:
            if fault and fault not in seen:
                seen.add(fault)
                collapsed_faults.append(fault)
# Count the unique faults that remain after collapsing.
total_faults_after_collapsing = len(collapsed_faults)
collapse_ratio = (
    total_faults_after_collapsing / total_faults_before_collapsing
    if total_faults_before_collapsing else 0
)
# Open the after-collapsing output file, replacing it if it already exists.
with open(module_name + "_AF.txt", "w") as file:
    for fault in collapsed_faults:
        signal, stuck_at = fault.rsplit("_", 1)
        file.write(f"{stuck_at} {signal}\n")
# Write the fault total, collapse ratio, and equivalent-classes heading.
    file.write(f"\nTotal Faults_AF = {total_faults_after_collapsing}\n")
    file.write(f"Collapse_ratio = {collapse_ratio:g}\n")
    file.write("\nEquivalent Classes:\n")
# Write each fault group as a comma-separated line in the equivalent-classes section.
    # Write each inner fault list as one class.
    for fault_group in new_processed_list:
        for faults in fault_group.values():
            formatted_faults = []
            for fault in sorted(faults) if isinstance(faults, set) else faults:
                if fault:
                    signal, stuck_at = fault.rsplit("_", 1)
                    formatted_faults.append(f"{stuck_at} {signal}")
            if formatted_faults:
                file.write(", ".join(formatted_faults) + "\n")

print(f"Please check the following files generated in the current working directory\n"+
      f"the output of the program\n"+
      f"1.{module_name}_AF.txt,\n"+  
      f"2.{module_name}_BF.txt\n" +
      f"3.faults_after_equivalence.txt"+ 
      "files. Please let me know if there is any confusion regarding the program.")