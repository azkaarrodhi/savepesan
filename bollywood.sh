#!/bin/bash

clear
toilet -f big "Bollywood" | lolcat
sleep 2

for i in {1..3}
do
    figlet "Get Ready!" | lolcat
    sleep 1
    clear
done

cmatrix -C red -u 5 &
MATRIX_PID=$!

sleep 5
kill $MATRIX_PID

clear
echo "Menampilkan efek teks Bollywood..." | lolcat
sleep 2

for i in {1..5}
do
    toilet -f mono12 -F metal "Dance $i" | lolcat
    sleep 1
done

clear
neofetch | lolcat


