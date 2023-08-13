# ProLaser III Control Console

This code interacts with a Kustom Signals ProLaser III speed lidar unit.

It reads speed packets from the lidar gun and reports them to a web app.

The code runs on MicroPython (Raspberry Pi Pico-W) as well as good-old-fashioned
desktop Python.  For desktop Python, this code requires the PySerial library.

The ProLaser III serial protocols were all reverse-engineered, I'm sure what
I have is not the complete list.  

This remains a work in progress.  Comments and input are welcome.
