.text
main:

# Same sign
li $t0, 300
li $t1, 200

bgt $t0, $t1, branch

li $a0, 0
li $v0, 1
syscall
j next

branch:
li $a0, 1
li $v0, 1
syscall

next:

# Diff sign
li $t0, 300
li $t1, -200

bgt $t0, $t1, branch_2

li $a0, 0
li $v0, 1
syscall
j next_2

branch_2:
li $a0, 1
li $v0, 1
syscall

next_2:

# Same sign
li $t0, 300
li $t1, 200

bgtu $t0, $t1, branch_3

li $a0, 0
li $v0, 1
syscall
j next_3

branch_3:
li $a0, 1
li $v0, 1
syscall

next_3:

li $t0, 300
li $t1, -200

bgtu $t0, $t1, branch_4

li $a0, 0
li $v0, 1
syscall
j next_4

branch_4:
li $a0, 1
li $v0, 1
syscall

next_4: