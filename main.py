from time import sleep
from threading import Thread, Event
from datetime import datetime
from zaber_motion import Library
from zaber_motion.ascii import Connection
import zaber_motion.exceptions as exc
import zaber_motion.units as uni
import matplotlib.pyplot as plt
import os
import sys

# ---- Global Events ----
pause_event = Event()
pause_event.set()
quit_event = Event()

# ---- Plot Setup ----
def setup_plot():
    plt.ion()
    fig, ax = plt.subplots()
    scat, = ax.plot([], [], 'ro')
    ax.set_xlim(0, 150)
    ax.set_ylim(0, 150)
    ax.set_xlabel('X Position (mm)')
    ax.set_ylabel('Y Position (mm)')
    ax.set_title('Live Scan Progress')
    plt.grid(True)
    return fig, ax, scat

# ---- Device Setup ----
def setup_devices():
    connection3 = Connection.open_serial_port('COM3')
    connection4 = Connection.open_serial_port('COM4')
    device_x = connection3.get_device(2)
    device_y = connection4.get_device(1)
    device_x.identify()
    device_y.identify()
    axis_x = device_x.get_axis(1)
    axis_y = device_y.get_axis(1)
    axis_x.settings['maxspeed'] = 1000 #Micrometers per second
    axis_y.settings['maxspeed'] = 1000 #Micrometers per second
    axis_x.home(wait_until_idle=True)
    axis_y.home(wait_until_idle=True)

    return axis_x, axis_y

# ---- Input Control ----
def start_input_listener():
    def input_listener():
        while True:
            command = input("Type 'p' to pause, 'r' to resume, or 'q' to quit: ").strip().lower()
            if command == 'p':
                print("⏸ Paused")
                pause_event.clear()
            elif command == 'r':
                print("▶️ Resumed")
                pause_event.set()
            elif command == 'q':
                print("🛑 Quit requested...")
                quit_event.set()
                break
    listener_thread = Thread(target=input_listener, daemon=True)
    listener_thread.start()

# ---- Scanning Logic ----
def scan_2d(axis_x, axis_y, fig, ax, scat, length, step_size, period, x_positions, y_positions):
    os.makedirs("scan_data", exist_ok=True)

    try:
        for step_x in range(round(length / step_size)):
            if quit_event.is_set():
                break

            axis_x.move_relative(step_size, unit=uni.Units.LENGTH_MILLIMETRES, wait_until_idle=True)
            axis_y.home(wait_until_idle=True)

            for step_y in range(round(length / step_size)):
                if quit_event.is_set():
                    break

                pause_event.wait()

                axis_y.move_relative(step_size, unit=uni.Units.LENGTH_MILLIMETRES, wait_until_idle=True)
                current_x = axis_x.get_position(unit=uni.Units.LENGTH_MILLIMETRES)
                current_y = axis_y.get_position(unit=uni.Units.LENGTH_MILLIMETRES)
                x_positions.append(current_x)
                y_positions.append(current_y)

                # Update plot
                scat.set_data(x_positions, y_positions)
                fig.canvas.draw()
                fig.canvas.flush_events()
                sleep(period)

                # Save file with timestamp
                now = datetime.now()
                time_str = now.strftime("%H-%M-%S")
                date_str = now.strftime("%d_%m_%Y")
                filename = f"{current_x:.2f}_{current_y:.2f}_{time_str}_{date_str}.txt"
                filepath = os.path.join("scan_data", filename)
                with open(filepath, 'w') as f:
                    f.write(f"Position: X={current_x:.2f} mm, Y={current_y:.2f} mm\n")
                    f.write(f"Timestamp: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")

    except BaseException as e:
        print(f"❌ Error during scan: {e}")

    plt.ioff()
    plt.show()

    if quit_event.is_set():
        print("✅ Scan stopped by user. Exiting cleanly.")
        sys.exit(0)

# ---- Main ----
def main():
    # ---- Parameters defined here ----
    length_x = 150 #millimeters
    length_y = 150 #millimeters
    step_size = 10 #millimeters
    period = 5  #seconds
    x_positions = [] #scanned xy combinations
    y_positions = [] #scanned xy combinations

    # ---- Execution ----
    start_input_listener()
    fig, ax, scat = setup_plot()
    axis_x, axis_y = setup_devices()
    scan_2d(axis_x, axis_y, fig, ax, scat, length, step_size, period, x_positions, y_positions)

if __name__ == "__main__":
    main()
