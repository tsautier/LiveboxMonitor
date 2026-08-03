### Livebox Monitor Scheduler dialog ###
#
# Internal schedule representation:
#   {
#       "Enable": True|False,         # global schedule enabled
#       "Days": [                     # 7 entries, Monday=0 .. Sunday=6
#           [ (start_min, end_min, active_bool), ... ],
#           ...
#       ]
#   }
#
# Intervals use minutes from 0 .. 1440 (end exclusive). Intervals are non-overlapping and merged.

from PyQt6 import QtCore, QtGui, QtWidgets

from LiveboxMonitor.app import LmConfig
from LiveboxMonitor.lang.LmLanguages import get_scheduler_label as lx
from LiveboxMonitor.tools import LmTools


# ################################ Scheduler dialog ################################
class SchedulerDialog(QtWidgets.QDialog):
    def __init__(self, parent, schedule=None):
        super().__init__(parent)

        self._app = parent
        self.resize(820, 420)

        # Internal context: if None supplied, create default full-activation schedule
        self._wifi_mode = False     # Wifi scheduler mode
        self._repeater = False      # Wifi repeater scheduler mode
        self._schedule = self.make_default_schedule() if schedule is None else self.convert_livebox_schedule(schedule)
        self.normalize_schedule()
        schedule_type = self._schedule.get("Type")

        # Top controls: global enable checkbox
        self._global_enable_checkbox = QtWidgets.QCheckBox(lx("Enable Schedule"), objectName="globalEnable")
        self._global_enable_checkbox.setChecked(bool(self._schedule.get("Enable", False)))
        self._global_enable_checkbox.toggled.connect(self.global_enable_toggled)

        # Timeline widget
        self._timeline = WeeklyTimelineWidget(self, schedule=self._schedule, objectName="timeline")
        self._timeline.scheduleChanged.connect(self.schedule_edited)

        # Editor controls
        editor_group = QtWidgets.QGroupBox(lx("Add Period"), objectName="editorGroup")
        editor_layout = QtWidgets.QGridLayout(editor_group)
        editor_layout.setSpacing(25)
        editor_layout.setColumnStretch(1, 1)
        editor_layout.setColumnStretch(3, 1)
        editor_layout.setColumnStretch(5, 1)

        # Start / End
        hhmm_reg_exp = QtCore.QRegularExpression(LmTools.HHMM_RS)
        hhmm_validator = QtGui.QRegularExpressionValidator(hhmm_reg_exp)

        editor_layout.addWidget(QtWidgets.QLabel(lx("Start (HH:MM)")), 0, 0)
        self._start_edit = QtWidgets.QLineEdit("00:00", objectName="startEdit")
        self._start_edit.setValidator(hhmm_validator)
        editor_layout.addWidget(self._start_edit, 0, 1)

        editor_layout.addWidget(QtWidgets.QLabel(lx("End (HH:MM)")), 0, 2)
        self._end_edit = QtWidgets.QLineEdit("24:00", objectName="endEdit")
        self._end_edit.setValidator(hhmm_validator)
        editor_layout.addWidget(self._end_edit, 0, 3)

        # Activate / Deactivate option
        editor_layout.addWidget(QtWidgets.QLabel(lx("Action")), 0, 4)
        self._action_combo = QtWidgets.QComboBox(objectName="actionCombo")
        self._action_combo.addItem(lx("Activate"))
        self._action_combo.addItem(lx("Deactivate"))
        editor_layout.addWidget(self._action_combo, 0, 5)

        # Days checkboxes (Mon..Sun) - Monday selected by default, at least one enforced
        editor_layout.addWidget(QtWidgets.QLabel(lx("Days")), 1, 0)
        days_widget = QtWidgets.QWidget(objectName="days")
        days_hbox = QtWidgets.QHBoxLayout(days_widget)
        days_hbox.setContentsMargins(0, 0, 0, 0)
        self._day_checks = []
        day_names = [lx("Mon"), lx("Tue"), lx("Wed"), lx("Thu"), lx("Fri"), lx("Sat"), lx("Sun")]
        for i, dn in enumerate(day_names):
            cb = QtWidgets.QCheckBox(dn)
            cb.clicked.connect(self.ensure_at_least_one_day)
            self._day_checks.append(cb)
            days_hbox.addWidget(cb)
        self._last_selected_day = 0     # Monday selected by default
        self._day_checks[self._last_selected_day].setChecked(True)
        editor_layout.addWidget(days_widget, 1, 1, 1, 5)

        # Apply button
        self._apply_button = QtWidgets.QPushButton(lx("Apply"), objectName="apply")
        self._apply_button.clicked.connect(self.apply_period)
        editor_layout.addWidget(self._apply_button, 2, 5, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # OK / Cancel
        self._sync_repeaters_checkbox = QtWidgets.QCheckBox(lx("Apply to all repeaters"), objectName="syncRepeaters")
        ok_button = QtWidgets.QPushButton(lx("OK"), objectName="ok")
        ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)
        cancel_button = QtWidgets.QPushButton(lx("Cancel"), objectName="cancel")
        cancel_button.clicked.connect(self.reject)
        button_bar = QtWidgets.QHBoxLayout()
        button_bar.setSpacing(10)
        if self._wifi_mode:
            button_bar.addWidget(self._sync_repeaters_checkbox, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        hbox = QtWidgets.QHBoxLayout()
        hbox.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
        hbox.setSpacing(10)
        hbox.addStretch(1)
        hbox.addWidget(ok_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        hbox.addWidget(cancel_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)
        button_bar.addLayout(hbox)

        # Layout assembly
        vbox = QtWidgets.QVBoxLayout(self)
        vbox.setSpacing(25)
        if self._wifi_mode:
            vbox.addWidget(self._global_enable_checkbox, 0)
        vbox.addWidget(self._timeline, 0)
        vbox.addWidget(editor_group, 0)
        vbox.addLayout(button_bar, 1)

        LmConfig.set_tooltips(self, "scheduler")

        self.setWindowTitle(lx("Schedule Editor"))
        self.setModal(True)
        self.show()


    # Get schedule in internal format
    def get_internal_schedule(self):
        return self._schedule


    # Get schedule in Livebox format
    def get_schedule(self):
        if self._repeater:
            return self.get_repeater_schedule()
        return SchedulerDialog.convert_internal_to_schedule(self._schedule)


    # Get schedule in repeater format
    def get_repeater_schedule(self):
        return SchedulerDialog.convert_internal_to_repeater_schedule(self._schedule)


    # Get sync repeaters option
    def get_sync_repeaters_option(self):
        return self._sync_repeaters_checkbox.isChecked()


    # Global enable checkbox clicked
    def global_enable_toggled(self, state):
        self._schedule["Enable"] = state


    # Schedule has been edited in the time table
    def schedule_edited(self, schedule):
        self._schedule = schedule


    # Day of the week checkbox clicked - ensure at least one remains selected
    def ensure_at_least_one_day(self):
        # Make sure at least one day is selected. If last selected is being unchecked, re-check it.
        checked = [cb.isChecked() for cb in self._day_checks]
        if not any(checked):
            # re-check last selected
            self._day_checks[self._last_selected_day].setChecked(True)
        else:
            self._last_selected_day = checked.index(True)


    # Apply entered period
    def apply_period(self):
        # Validate times
        try:
            s = self.hhmm_to_minutes(self._start_edit.text().strip())
            e = self.hhmm_to_minutes(self._end_edit.text().strip())
        except Exception as ex:
            self._app.display_error(lx("Please enter times in HH:MM format (00:00 .. 24:00)."))
            return
        if e <= s:
            self._app.display_error(lx("The end time must be greater than the start time."))
            return
        active = (self._action_combo.currentIndex() == 0)
        days = [i for i, cb in enumerate(self._day_checks) if cb.isChecked()]
        if not days:
            self._app.display_error(lx("You must select at least one day."))
            return

        # Apply to selected days
        for d in days:
            self._schedule["Days"][d].append((s, e, active))

        # Ensure final normalization across all days
        self.normalize_schedule(not active)
        self._timeline.set_schedule(self._schedule)



    ### Normalize internal schedule structure
    def normalize_schedule(self, priority_to_disabled=True):
        """
        - Ensures full coverage from minute 0 to 1440 for each day.
        - Merges contiguous periods with the same Enable value.
        - Resolves overlaps and inclusions based on priority.
        - Sorts periods chronologically.
        """
        normalized_days = []

        def has_priority(new_state, existing_state):
            if new_state == existing_state:
                return False
            if priority_to_disabled:
                return new_state is False  # False wins over True
            else:
                return new_state is True   # True wins over False

        for day_periods in self._schedule.get("Days", []):
            # 1440 minute slots for the day. Each slot stores: (state, is_explicit)
            schedule_arr = [(False, False)] * 1440
            
            for start, end, active in day_periods:
                start = max(0, min(1440, start))
                end = max(0, min(1440, end))
                if start >= end:
                    continue
                
                for m in range(start, end):
                    ex_state, ex_explicit = schedule_arr[m]
                    if not ex_explicit:
                        schedule_arr[m] = (active, True)
                    else:
                        if has_priority(active, ex_state):
                            schedule_arr[m] = (active, True)

            # Reconstruct contiguous periods from the minute array
            new_day_periods = []
            if not schedule_arr:
                new_day_periods.append((0, 1440, False))
            else:
                curr_state = schedule_arr[0][0]
                seg_start = 0
                for m in range(1, 1440):
                    state = schedule_arr[m][0]
                    if state != curr_state:
                        new_day_periods.append((seg_start, m, curr_state))
                        seg_start = m
                        curr_state = state
                new_day_periods.append((seg_start, 1440, curr_state))

            normalized_days.append(new_day_periods)

        self._schedule["Days"] = normalized_days


    # Build a default schedule with full activation for all days
    @staticmethod
    def make_default_schedule():
        full_day = [(0, 1440, True)]
        return {"Enable": False, "Days": [full_day for _ in range(7)]}


    # Convert a schedule returned by Livebox Wifi API to internal format
    def convert_livebox_schedule(self, schedule):
        try:
            if not isinstance(schedule, dict):
                LmTools.error("Schedule is not a dictionnary")
                return SchedulerDialog.make_default_schedule()

            sched_type = schedule.get("Type", "Wifi")
            self._wifi_mode = (sched_type == "Wifi") or (sched_type == "Repeater")

            if schedule.get("Schedule"):
                self._wifi_mode = True
                if sched_type == "Repeater":
                    self._repeater = True
                    return SchedulerDialog.convert_repeater_schedule_to_internal(schedule)
                else:
                    return SchedulerDialog.convert_schedule_to_internal(schedule)
            else:
                LmTools.log_debug(1, "Empty schedule, use default")
                return SchedulerDialog.make_default_schedule()

        except Exception as e:
            LmTools.error(str(e))
            return SchedulerDialog.make_default_schedule()


    # Convert a normal schedule returned by Livebox Wifi API to internal format
    @staticmethod
    def convert_schedule_to_internal(schedule):
        global_enable = schedule.get("Enable", True)
        schedule_dict = schedule.get("Schedule", {})

        points = []
        for key, entry in schedule_dict.items():
            ext_day = entry.get("Day", 1)
            day_idx = ext_day - 1  # External 1..7 -> Internal 0..6
            if 0 <= day_idx < 7:
                hour = entry.get("Hour", 0)
                minute = entry.get("Minute", 0)
                second = entry.get("Second", 0)
                # Calculate absolute minute from the start of the week
                abs_min = (day_idx * 1440) + (hour * 60) + minute + (1 if second >= 30 else 0)
                enable = entry.get("Enable", False)
                points.append((abs_min, enable))

        # Sort change points chronologically across the week
        points.sort(key=lambda x: x[0])

        # Rule: if nothing before 00h00:00 assume disabled
        if not points or points[0][0] > 0:
            points.insert(0, (0, False))

        total_week_minutes = 7 * 1440  # 10080 minutes in a week
        full_week_intervals = []

        for i in range(len(points)):
            start_min, active = points[i]
            end_min = points[i + 1][0] if i + 1 < len(points) else total_week_minutes
            if start_min < end_min:
                full_week_intervals.append((start_min, end_min, active))

        # Split weekly absolute intervals back across the 7 days (0 to 1440 minutes per day)
        days_periods = [[] for _ in range(7)]

        for s, e, active in full_week_intervals:
            while s < e:
                day_idx = s // 1440
                if day_idx >= 7:
                    break
                day_start_min = day_idx * 1440
                day_end_min = (day_idx + 1) * 1440
                chunk_end = min(e, day_end_min)

                day_rel_start = s - day_start_min
                day_rel_end = chunk_end - day_start_min

                if day_rel_start < day_rel_end:
                    days_periods[day_idx].append((day_rel_start, day_rel_end, active))

                s = chunk_end

        return {"Enable": global_enable, "Days": days_periods}


    # Convert a repeater schedule returned by Livebox Wifi API to internal format
    @staticmethod
    def convert_repeater_schedule_to_internal(schedule):
        global_enable = schedule.get("Enable", True)
        schedule_list = schedule.get("Schedule", [])

        repeater_intervals = []
        for item in schedule_list:
            state_str = item.get("state", "Disable")
            active = True if state_str.lower() == "enable" else False
            begin = item.get("begin", 0)
            end = item.get("end", 0)
            if begin < end:
                repeater_intervals.append((begin, end, active))

        repeater_intervals.sort(key=lambda x: x[0])

        # Fill gaps (holes) with Enable = True periods
        full_week_intervals = []
        curr = 0
        total_week_seconds = 7 * 24 * 3600  # 604,800 seconds in a week

        for b, e, active in repeater_intervals:
            if b > curr:
                full_week_intervals.append((curr, b, True))
            full_week_intervals.append((b, e, active))
            curr = max(curr, e)

        if curr < total_week_seconds:
            full_week_intervals.append((curr, total_week_seconds, True))

        # Split weekly intervals across the 7 days (0 to 1440 minutes per day)
        days_periods = [[] for _ in range(7)]
        sec_per_day = 86400

        for s, e, active in full_week_intervals:
            while s < e:
                day_idx = s // sec_per_day
                if day_idx >= 7:
                    break
                day_start_sec = day_idx * sec_per_day
                day_end_sec = (day_idx + 1) * sec_per_day
                chunk_end = min(e, day_end_sec)

                start_min = (s - day_start_sec) // 60
                end_min = (chunk_end - day_start_sec) // 60

                if start_min < end_min:
                    days_periods[day_idx].append((start_min, end_min, active))

                s = chunk_end

        return {"Enable": global_enable, "Days": days_periods}


    # Helper function to flatten week days into absolute minute intervals from the start of the week
    @staticmethod
    def get_absolute_periods(internal_schedule):
        abs_periods = []
        for day_idx, day_periods in enumerate(internal_schedule["Days"]):
            day_offset = day_idx * 1440  # 1440 minutes per day
            for start_min, end_min, active_bool in day_periods:
                abs_start = day_offset + start_min
                abs_end = day_offset + end_min
                abs_periods.append((abs_start, abs_end, active_bool))
        return abs_periods


    # Convert an internal schedule to normal schedule format used by Livebox Wifi API 
    @staticmethod
    def convert_internal_to_schedule(internal_schedule):
        abs_periods = SchedulerDialog.get_absolute_periods(internal_schedule)
        schedule_list = []

        last_state = None
        for abs_start, abs_end, active_bool in abs_periods:
            # Emit an entry if it's the very first point of the week or if the state changes
            if (abs_start == 0) or (active_bool != last_state):
                day = (abs_start // 1440) + 1  # 0-indexed day to 1-7 format
                hour = (abs_start % 1440) // 60
                minute = (abs_start % 1440) % 60

                schedule_list.append({
                    "Day": day,
                    "Hour": hour,
                    "Minute": minute,
                    "Second": 0,
                    "enable": active_bool
                })

            last_state = active_bool

        return {
            "Enable": internal_schedule["Enable"],
            "Type": "Wifi",
            "Schedule": schedule_list
        }


    # Convert an internal schedule to repeater schedule format used by Livebox Wifi API 
    @staticmethod
    def convert_internal_to_repeater_schedule(internal_schedule):
        abs_periods = SchedulerDialog.get_absolute_periods(internal_schedule)
        schedule_list = []

        current_disable_start = None
        current_disable_end = None

        for abs_start, abs_end, active_bool in abs_periods:
            if not active_bool:
                if current_disable_start is None:
                    current_disable_start = abs_start
                    current_disable_end = abs_end
                elif abs_start == current_disable_end:
                    # Merge contiguous disabled periods
                    current_disable_end = abs_end
                else:
                    # Flush previous disabled block and start a new one
                    schedule_list.append({
                        "state": "Disable",
                        "begin": current_disable_start * 60,
                        "end": current_disable_end * 60
                    })
                    current_disable_start = abs_start
                    current_disable_end = abs_end
            else:
                # Active period reached; flush any ongoing disabled block
                if current_disable_start is not None:
                    schedule_list.append({
                        "state": "Disable",
                        "begin": current_disable_start * 60,
                        "end": current_disable_end * 60
                    })
                    current_disable_start = None
                    current_disable_end = None

        # Flush final disabled block if week ends while disabled
        if current_disable_start is not None:
            schedule_list.append({
                "state": "Disable",
                "begin": current_disable_start * 60,
                "end": current_disable_end * 60
            })

        return {
            "Enable": internal_schedule["Enable"],
            "Type": "Repeater",
            "Schedule": schedule_list
        }


    # Convert 'HH:MM' string to minutes (0..1439). Raises ValueError on invalid format.
    @staticmethod
    def hhmm_to_minutes(hhmm_str):
        parts = hhmm_str.split(":")
        if len(parts) != 2:
            raise ValueError("Bad time format")
        hh = int(parts[0])
        mm = int(parts[1])
        if not (((0 <= hh <= 23) and (0 <= mm <= 59)) or ((hh == 24) and (mm == 0))):
            raise ValueError("Bad time values")
        return (hh * 60) + mm


    # Convert minutes (0..1439) to a 'HH:MM' string
    @staticmethod
    def minutes_to_hhmm(minutes):
        h = minutes // 60
        mm = minutes % 60
        return f"{h:02d}:{mm:02d}"



# ################################ Timeline widget ################################
class WeeklyTimelineWidget(QtWidgets.QWidget):
    """
    Paint and edit a 7-line weekly timeline (Mon..Sun) with 15-minute granularity.
    Each line displays colored segments:
      - Active (True): light green
      - Inactive (False): light red    
    Signals:
        scheduleChanged(dict): Emitted when the user finishes editing the schedule via mouse interaction.
    """
    HEADER = 15
    ROW_HEIGHT = 25
    LEFT_MARGIN = 50
    RIGHT_MARGIN = 10

    # Signal emitted when schedule is modified by user interaction
    scheduleChanged = QtCore.pyqtSignal(dict)

    def __init__(self, parent=None, schedule=None, objectName=None):
        super().__init__(parent, objectName=objectName)
        self._schedule = None

        # Interaction state tracking
        self._is_dragging = False
        self._drag_target_state = False
        self._working_grid = None  # 7 x 96 boolean grid during active drag
        self._last_day = None
        self._last_slot = None

        self.setMinimumHeight(self.HEADER + (self.ROW_HEIGHT * 7))
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding, 
            QtWidgets.QSizePolicy.Policy.Expanding
        )

        # Enable mouse tracking for smooth drag handling
        self.setMouseTracking(False)
        self.set_schedule(schedule)


    # Update internal schedule and refresh display
    def set_schedule(self, schedule):
        if schedule is None:
            # Default empty schedule (7 days, all inactive)
            self._schedule = {
                "Enable": True,
                "Days": [[(0, 1440, False)] for _ in range(7)]
            }
        else:
            self._schedule = schedule
            
        self.update()


    # Return current schedule data structure
    def get_schedule(self):
        return self._schedule


    # Convert schedule intervals into a 7x96 boolean grid (15-min slots)
    def schedule_to_grid(self, schedule):
        grid = []
        days_data = schedule.get("Days", []) if schedule else []

        for day_idx in range(7):
            day_slots = [False] * 96
            if day_idx < len(days_data):
                intervals = days_data[day_idx]
                for start_min, end_min, active in intervals:
                    start_slot = max(0, min(95, start_min // 15))
                    end_slot = max(0, min(96, (end_min + 14) // 15))
                    for slot in range(start_slot, end_slot):
                        day_slots[slot] = bool(active)
            grid.append(day_slots)
        return grid


    # Convert a 7x96 boolean grid back into schedule interval format
    def grid_to_schedule(self, grid):
        enable_flag = self._schedule.get("Enable", True) if self._schedule else True
        days_intervals = []

        for day_slots in grid:
            intervals = []
            curr_start_slot = 0
            curr_state = day_slots[0]

            for slot_idx in range(1, 96):
                if day_slots[slot_idx] != curr_state:
                    intervals.append((curr_start_slot * 15, slot_idx * 15, curr_state))
                    curr_start_slot = slot_idx
                    curr_state = day_slots[slot_idx]

            # Close final interval for the day
            intervals.append((curr_start_slot * 15, 1440, curr_state))
            days_intervals.append(intervals)

        return {"Enable": enable_flag, "Days": days_intervals}


    # Map mouse position (QPoint) to (day_index 0..6, slot_index 0..95)
    def pos_to_day_slot(self, pos):
        rect = self.rect()
        total_width = max(100, rect.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN)
        row_height = max(1, int((rect.height() - self.HEADER) / 7))

        # Determine day index
        y_rel = pos.y() - self.HEADER
        day_idx = int(y_rel // row_height)
        day_idx = max(0, min(6, day_idx))

        # Determine 15-min slot index (0..95)
        x_rel = pos.x() - self.LEFT_MARGIN
        slot_idx = int((x_rel / total_width) * 96)
        slot_idx = max(0, min(95, slot_idx))

        return day_idx, slot_idx


    # Set a single slot in the working grid to the target drag state
    def apply_drag_to_slot(self, day_idx, slot_idx):
        if self._working_grid and (0 <= day_idx < 7) and (0 <= slot_idx < 96):
            self._working_grid[day_idx][slot_idx] = self._drag_target_state


    # Linearly interpolate slots between two mouse positions during drag
    def interpolate_and_apply(self, day1, slot1, day2, slot2):
        steps = max(abs(day2 - day1), abs(slot2 - slot1))
        if steps == 0:
            self.apply_drag_to_slot(day2, slot2)
            return

        for i in range(steps + 1):
            t = i / steps
            d = int(round(day1 + t * (day2 - day1)))
            s = int(round(slot1 + t * (slot2 - slot1)))
            self.apply_drag_to_slot(d, s)


    # Mouse click event
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            rect = self.rect()

            # Check if click is inside timeline area
            if ((self.LEFT_MARGIN <= event.position().x() <= rect.width() - self.RIGHT_MARGIN) and
                (self.HEADER <= event.position().y() <= rect.height())):

                day_idx, slot_idx = self.pos_to_day_slot(event.position())

                # Initialize working grid from current schedule
                self._working_grid = self.schedule_to_grid(self._schedule)

                # Determine mode: Active -> Deactivate (False), Inactive -> Activate (True)
                initial_state = self._working_grid[day_idx][slot_idx]
                self._drag_target_state = not initial_state
                self._is_dragging = True

                # Apply change to clicked slot
                self.apply_drag_to_slot(day_idx, slot_idx)
                self._last_day, self._last_slot = day_idx, slot_idx

                self.update()


    # Mouse move event
    def mouseMoveEvent(self, event):
        if self._is_dragging and (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            day_idx, slot_idx = self.pos_to_day_slot(event.position())

            # Fill intermediate slots between last position and current position
            self.interpolate_and_apply(self._last_day, self._last_slot, day_idx, slot_idx)
            self._last_day, self._last_slot = day_idx, slot_idx

            self.update()


    # Mouse button release event
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False

            # Commit changes to internal schedule
            self._schedule = self.grid_to_schedule(self._working_grid)
            self._working_grid = None

            self.update()

            # Emit signal with the new schedule structure
            self.scheduleChanged.emit(self._schedule)


    # Painting
    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        rect = self.rect()
        total_width = max(100, rect.width() - self.LEFT_MARGIN - self.RIGHT_MARGIN)
        row_height = max(1, int((rect.height() - self.HEADER) / 7))
        y = self.HEADER

        # Fonts
        font = qp.font()
        font.setPointSize(9)
        qp.setFont(font)

        # Colors
        active_color = QtGui.QColor(200, 255, 200)
        inactive_color = QtGui.QColor(255, 200, 200)
        border_color = QtGui.QColor(150, 150, 150)

        # Retrieve intervals to draw (use temporary grid if dragging, otherwise self._schedule)
        if self._is_dragging and self._working_grid:
            active_schedule = self.grid_to_schedule(self._working_grid)
        else:
            active_schedule = self._schedule

        # Draw each day line
        day_names = [lx("Mon"), lx("Tue"), lx("Wed"), lx("Thu"), lx("Fri"), lx("Sat"), lx("Sun")]
        for day_idx in range(7):
            y_row = y + (day_idx * row_height)

            # Background
            qp.setPen(QtGui.QPen(border_color))
            qp.setBrush(QtGui.QBrush(QtGui.QColor(245, 245, 245)))
            qp.drawRect(self.LEFT_MARGIN, y_row, total_width, row_height - 4)

            # Day label
            qp.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
            qp.drawText(8, y_row + (row_height // 2) + 5, day_names[day_idx])

            # Draw active/inactive intervals
            if active_schedule and "Days" in active_schedule:
                day_intervals = active_schedule["Days"][day_idx]
                for s, e, a in day_intervals:
                    x1 = self.LEFT_MARGIN + int((s / 1440.0) * total_width)
                    x2 = self.LEFT_MARGIN + int((e / 1440.0) * total_width)
                    qp.setBrush(QtGui.QBrush(active_color if a else inactive_color))
                    qp.setPen(QtGui.QPen(QtGui.QColor(120, 120, 120)))
                    qp.drawRect(x1, y_row + 2, max(1, x2 - x1), row_height - 8)

        # Draw hour separators and labels on top
        for h in range(25):
            x = self.LEFT_MARGIN + int((h / 24.0) * total_width)
            qp.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180)))
            qp.drawLine(x, y - 5, x, y + (7 * row_height) - 4)

            # Hour label
            qp.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
            qp.drawText(x - 8, y - 6, f"{h}h")

        qp.end()
