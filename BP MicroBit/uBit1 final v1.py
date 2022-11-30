from microbit import *
import log
from ssd1306_necessary import *

pinhb = pin10
pinbp = pin1
pinpump = pin2
pinvalve = pin8
pinled_r = pin3
pinled_g = pin4
pinled_b = pin6

pinspk = pin0
pinsound = pin7  # pinsound 1 when user requires sound

pinreadBT = pin16

display.off()

ticks = 0
dt = 5  # number of milliseconds for one tick

sleep(500)

log.set_labels("sys", "dia", "hb_rate")

uart.init(baudrate=115200, bits=8, parity=None, stop=1, tx=pin14, rx=pin15)

# initialize variables
hb_current = pinhb.read_analog()
hb_avg = pinhb.read_analog()
bp_current = pinbp.read_analog() * 0.258 - 24

# initialize arrays
ahb_current = []
ahb_avg = []
abp_current = []

for i in range(0, 10):
    ahb_current.insert(0, hb_current)
    abp_current.insert(0, bp_current)
for i in range(0, 30):
    ahb_avg.insert(0, hb_avg)

initialize()
clear_oled()

pinvalve.write_digital(0)  # open valve

if (pinsound.read_digital()):
    speech.say("Welcome, press- A to begin, press- A again to stop.")
pinspk.write_digital(0)  # turn off speaker to prevent amplification of noises

def mean(array):
    sum = 0
    for i in array:
        sum += i
    return sum / len(array)

def updateticks():
    sleep(dt)
    global ticks
    if (ticks < 9999):
        ticks += 1
    else:
        ticks = 0

def updatedata():
    global ahb_current, ahb_avg, abp_current, hb_current, hb_avg, bp_current

    hb = pinhb.read_analog()
    bp = pinbp.read_analog() * 0.258 - 24

    ahb_current.append(hb)
    abp_current.append(bp)

    ahb_current.pop(0)
    abp_current.pop(0)

    hb_current = mean(ahb_current)
    bp_current = mean(abp_current)

    # update average hb every 30 ticks
    if (ticks % 10 == 0):
        ahb_avg.append(hb)
        ahb_avg.pop(0)
        hb_avg = mean(ahb_avg)

    # print((hb_current, bp_current))

def led_off():
    pinled_r.write_digital(0)
    pinled_g.write_digital(0)
    pinled_b.write_digital(0)
led_off()

ledval_r = 255
ledval_g = 1
ledval_b = 127
dledval_r = -1
dledval_g = 1
dledval_b = -1
def ledfade():
    global ledval_r, ledval_g, ledval_b, dledval_r, dledval_g, dledval_b

    pinled_r.write_analog(ledval_r)
    pinled_g.write_analog(ledval_g)
    pinled_b.write_analog(ledval_b)

    ledval_r += dledval_r
    ledval_g += dledval_g
    ledval_b += dledval_b

    if ((ledval_r >= 255) or (ledval_r <= 0)):
        dledval_r *= -1
    if ((ledval_g >= 255) or (ledval_g <= 0)):
        dledval_g *= -1
    if ((ledval_b >= 255) or (ledval_b <= 0)):
        dledval_b *= -1


def measurebp():
    # ############### Pump Up to 185 mmHg ###############
    pumprate = 600

    updatedata()
    clear_oled()
    led_off()

    pinvalve.write_digital(1)  # close valve
    pinpump.write_analog(pumprate)  # start pump

    emerstop = False  # to detect if emergency stop button is pressed

    # sleep for 200 ticks
    for i in range(0, 200):
        updateticks()
        updatedata()
        ledfade()
        if (ticks % 25 == 0):
            add_text(0, 0, "P= " + str(round(bp_current)) + "  ")

    while (bp_current < 185):  # wait until pressure >= 180 mmHg
        updateticks()
        updatedata()
        ledfade()
        if (ticks % 25 == 0):
            add_text(0, 0, "P= " + str(round(bp_current)) + "  ")

        if (button_a.is_pressed()):  # emergency stop
            emerstop = True
            break

    pinpump.write_digital(0)  # stop pump

    # sleep for 500 ticks while updating data, so pinhb can return to around 512.
    for i in range(0, 500):
        updateticks()
        updatedata()
        ledfade()
        if (ticks % 25 == 0):
            add_text(0, 0, "P= " + str(round(bp_current)) + "  ")

        if (button_a.is_pressed()):  # emergency stop
            emerstop = True
            break
    # pressure value drops to around 150 mmHg at the end of the sleep.

    # ############### Measure Heartbeat Amplitude ###############

    # initialize variables for measurment of hb pulse amplitude
    hb_max = 0
    hb_min = 1023
    max_reached = False
    min_reached = False
    amp_avg = 2048
    aamp = []
    count = -4  # counts the number of times a heartbeat is detected
    hb_tickdiff = 1
    # flag_rising = False  # to detect when heartbeat is rising, for measuring hb

    """
    hb_period = []  # for calculation of average period of heartbeat pulses
    hb_tick = "0"
    """

    # ticks2 = 0  # for counting number of cycles since the start of measuring the bp
    # sys_found = False
    # dia_found = False

    a_amp = []
    a_p = []

    amp_max = 0
    # modify to calibrate measured pressure
    thres_sys = 0.55
    thres_dia = 0.85

    while True:
        updatedata()
        updateticks()
        ledfade()

        if not(max_reached):
            if (hb_current > hb_max):
                hb_max = hb_current
            else:
                if (hb_max - hb_current > 10):
                    max_reached = True

        if not(min_reached):
            if (hb_current < hb_min):
                hb_min = hb_current
            else:
                if (hb_current - hb_min > 20):
                    min_reached = True

        if (max_reached and min_reached):
            amp_avg = abs(hb_max - hb_min)

            if (len(aamp) >= 10):
                aamp.append(amp_avg)
                aamp.pop(0)
            else:
                aamp.append(amp_avg)

            amp_avg = mean(aamp)

            a_amp.append(round(amp_avg))
            a_p.append(round(bp_current))

            count += 1
            if (count == 1):
                hb_tickdiff = running_time()

            # to find maximum amplitude, so cuff can be released earlier.
            if (count >= 1):
                if (amp_avg > amp_max):
                    amp_max = amp_avg

            # reset variables
            hb_max = 0
            hb_min = 1023
            max_reached = False
            min_reached = False

        hb_thres = 0.25

        stamp_heart = create_stamp(Image.HEART)
        # led_max = 500
        # level = 0
        if (hb_current - hb_avg > hb_thres * amp_avg):
            # level = min(led_max, max(0, 2.5 * (hb_current - hb_avg)))
            # pinled_r.write_analog(level)
            draw_stamp(123, 0, stamp_heart, 1)
            """
            if not(flag_rising):
                if (not(isinstance(hb_tick, str)) and (ticks - int(hb_tick) > 0)):
                    hb_period.append(ticks - int(hb_tick))
                hb_tick = ticks
                # flag_rising = True
            """
        else:
            # pinled_r.write_digital(0)
            draw_stamp(123, 0, stamp_heart, 0)
            # flag_rising = False

        if (ticks % 25 == 0):
            add_text(0, 0, "P= " + str(round(bp_current)) + "  ")

        if ((bp_current < 50) or (amp_avg < amp_max * (thres_dia - 0.2))):
            break

        if (button_a.is_pressed()):  # emergency stop
            emerstop = True
            break

    if (emerstop):  # prevent data evaluation if emergency stop detected  #################################3
        clear_oled()
        pinpump.write_digital(0)
        pinvalve.write_digital(0)
        add_text(0, 0, "EMERGENCY")
        add_text(0, 1, "STOP")
        add_text(0, 2, "DETECTED!")
        sleep(500)
    else:
        # ############### Evaluate the Recorded Data ###############

        pinvalve.write_digital(0)  # open valve

        clear_oled()
        led_off()

        hb_rate = 0
        if (running_time() > hb_tickdiff):
            hb_tickdiff = running_time() - hb_tickdiff
            hb_rate = round(60 * 1000 / hb_tickdiff * count / 2)
            # print(str(running_time()) + " " + str(hb_tickdiff) + " " + str(count))

        """
        for i in range(0, len(a_amp)):
            print((a_p[i], a_amp[i]))
        """

        amp_max = 0
        for i in range(0, len(a_amp)):
            if (a_amp[i] > amp_max):
                amp_max = a_amp[i]

        # calculate sys and dia amplitude
        amp_sys = thres_sys * amp_max
        amp_dia = thres_dia * amp_max
        bp_sys = 0
        bp_dia = 0

        # find sys pressure
        diff_min = 1023
        i = 0
        while (a_amp[i] < amp_max):
            diff = abs(amp_sys - a_amp[i])
            if (diff < diff_min):
                diff_min = diff
                if ((i - 1) < 0):
                    bp_sys = a_p[i]
                else:
                    bp_sys = round((a_p[i - 1] + a_p[i] + a_p[i + 1]) / 3)
            i += 1

        # find dia pressure
        diff_min = 1023
        i = len(a_amp) - 1
        while (a_amp[i] < amp_max):
            diff = abs(amp_dia - a_amp[i])
            if (diff < diff_min):
                diff_min = diff
                if ((i + 1) > (len(a_amp) - 1)):
                    bp_dia = a_p[i]
                else:
                    bp_dia = round((a_p[i - 1] + a_p[i] + a_p[i + 1]) / 3)
            i -= 1

        """
        # find heartbeat rate
        hb_rate = 0
        if (not(mean(hb_period) == 0)):
            hb_rate = round(60 * 1000 / mean(hb_period) / 13)  # one tick = around 13 ms
        """

        ############### Print Data and Present LED Feedback ###############

        add_text(0, 1, "SYS= " + str(bp_sys))
        add_text(0, 2, "DIA= " + str(bp_dia))
        add_text(0, 3, "HB = " + str(hb_rate))

        # for demonstration
        # bp_sys = 125
        # bp_dia = 70

        if (pinsound.read_digital()):
            speech.say("Your systolic pressure is " + str(bp_sys) + ".")
            speech.say("Your diastolic pressure is " + str(bp_dia) + ".")
            speech.say("Your heartbeat rate is " + str(hb_rate) + ".")

        # data from American Heart Association
        if ((bp_sys >= 140) or (bp_dia >= 90)):
            # led show red
            pinled_r.write_analog(255)

            add_text(0, 0, "Very high")

            if (pinsound.read_digital()):
                speech.say("Your blood pressure is fatally high.")
                speech.say("Please consult a doctor now.")
        elif ((bp_sys >= 130) or (bp_dia >= 80)):
            # led show orange
            pinled_r.write_analog(255)
            pinled_g.write_analog(50)

            add_text(0, 0, "High")

            if (pinsound.read_digital()):
                speech.say("Your blood pressure is high.")
                speech.say("You should have medical attention.")
        elif (bp_sys >= 120):
            # led show yellow
            pinled_r.write_analog(255)
            pinled_g.write_analog(140)

            add_text(0, 0, "Elevated")

            if (pinsound.read_digital()):
                speech.say("Your blood pressure is elevated.")
                speech.say("Medical attention is recommended.")
        else:
            # led show green
            pinled_g.write_analog(255)

            add_text(0, 0, "Normal")

            if (pinsound.read_digital()):
                speech.say("Your blood pressure is normal.")

        pinspk.write_digital(0)  # turn off speaker to prevent amplification of noises

        # send recorded data to the other microbit
        dt2 = 1200
        """
        sleep(dt2)
        uart.write(str(bp_sys) + "\n")
        sleep(dt2)
        uart.write(str(bp_dia) + "\n")
        sleep(dt2)
        uart.write(str(hb_rate) + "\n")
        """
        sleep(dt2)
        uart.write("Systolic: " + str(bp_sys) + "\n")
        sleep(dt2)
        uart.write("Diastolic: " + str(bp_dia) + "\n")
        sleep(dt2)
        uart.write("Heartbeat Rate: " + str(hb_rate) + "\n")

        log.add(sys=bp_sys, dia=bp_dia, hb_rate=hb_rate)

    """
    # sleep for 5000 ticks, then clear oled screen
    for i in range(0, 5000):
        updateticks()
        if (button_a.is_pressed()):
            break
    clear_oled()
    led_off()
    """
    sleep(500)

while True:
    updateticks()  # 1 tick = 5 ms

    if ((button_a.is_pressed()) or (pinreadBT.read_digital())):
        measurebp()
