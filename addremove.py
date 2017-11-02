import phaselist

results = [['Quartz', 789, '54.7'], ['Albite', 2264, '25.7'], ['Enstatite', 1201, '8.7'], ['Sanidine', 12862, '6.8'], ['Pyrite', 606, '4.1']]

selected = [a[0] for a in results]
available = []

# print selected

# inventory = phaselist.rockPhasesj
# print inventory

inventory= [a.split('\t') for a in phaselist.rockPhases]
name = [a[0] for a in inventory]
code = [a[1] for a in inventory]

#print name
#print code

# for i in range(0, len(phaselist.rockPhases)):
#     if selected[i] in phaselist.rockPhases[i]:
#         print "yes"
i = 0
while i < len(name):
    if any(word in name[i] for word in selected):
        print i, name[i]
        del name[i], code[i]
    i += 1

# print name
    
for i in range(len(name)):
    available.append(name[i]+'\t'+code[i])
    
# selected = [name+code for a in name]
    
#selected = [name[0]+'\t'+str(a[1]) for a in results]
#selected = [(name, code) for a in name]   
print available
print selected
selected = [a[0]+'\t'+str(a[1]) for a in results]
print selected
