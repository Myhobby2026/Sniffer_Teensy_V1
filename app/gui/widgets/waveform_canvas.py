import tkinter as tk
import math

class WaveformCanvas(tk.Canvas):
    """Virtualized waveform. Data: list of (abs_cycles, sample). f_cpu for time conversion."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg="#1E1E1E", highlightthickness=0, **kwargs)
        self.data = []  # list of (cycles, sample)
        self.f_cpu = 600_000_000
        self.channels = [{"id":i,"label":f"CH{i}","enabled":True,"color":f"#%06x"%(0x00BFFF + i*0x111111)} for i in range(16)]
        self.t0 = 0
        self.sec_per_px = 1e-5  # 10us per px initial
        self.y_per_ch = 28
        self.x_offset = 80
        self.cursors = []  # list of cycle positions
        self.trigger_cycle = None
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", self._on_wheel)
        self.bind("<Button-5>", self._on_wheel)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonPress-1>", self._on_click)
        self._drag_start_x = None
        self._drag_start_spp = None

    def set_data(self, data, f_cpu: int = 600_000_000, channels=None, trigger_cycle=None):
        self.data = data or []
        self.f_cpu = f_cpu
        if channels:
            self.channels = channels
        self.trigger_cycle = trigger_cycle
        if data:
            self.t0 = data[0][0]
        self.redraw()

    def _on_wheel(self, event):
        # Zoom centered on mouse
        mx = event.x
        factor = 0.9 if (event.delta > 0 if hasattr(event, "delta") else event.num==4) else 1.1
        old_spp = self.sec_per_px
        new_spp = old_spp * factor
        new_spp = max(1e-9, min(new_spp, 1e-2))
        # Keep mouse time stationary
        mouse_cycles = self.t0 + int((mx - self.x_offset) * old_spp * self.f_cpu)
        self.sec_per_px = new_spp
        # adjust t0 so mouse_cycles stays
        self.t0 = int(mouse_cycles - (mx - self.x_offset) * new_spp * self.f_cpu)
        self.redraw()

    def _on_click(self, event):
        self._drag_start_x = event.x
        self._drag_start_spp = self.sec_per_px
        # place cursor if near top? single cursor toggle
        if event.y < 20:
            # ruler click -> place cursor
            cyc = self.t0 + int((event.x - self.x_offset) * self.sec_per_px * self.f_cpu)
            if len(self.cursors) < 2:
                self.cursors.append(cyc)
            else:
                # replace nearest
                dists = [abs(c - cyc) for c in self.cursors]
                idx = dists.index(min(dists))
                self.cursors[idx] = cyc
            self.redraw()
        elif event.state & 0x4:  # ctrl
            cyc = self.t0 + int((event.x - self.x_offset) * self.sec_per_px * self.f_cpu)
            self.cursors.append(cyc)
            if len(self.cursors) > 2: self.cursors = self.cursors[-2:]
            self.redraw()

    def _on_drag(self, event):
        if self._drag_start_x is None:
            return
        dx = event.x - self._drag_start_x
        # pan: move t0 opposite
        delta_cycles = int(dx * self.sec_per_px * self.f_cpu)
        self.t0 -= delta_cycles
        self._drag_start_x = event.x
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = self.winfo_width() or 1200
        h = self.winfo_height() or 500
        if not self.data:
            self.create_text(w//2, h//2, text="No capture — connect device and start capture", fill="#9E9E9E", font=("Segoe UI", 11))
            return
        # time range visible
        visible_start = self.t0
        visible_end = self.t0 + int((w - self.x_offset) * self.sec_per_px * self.f_cpu)
        # Filter data to visible window + margin
        # quick binary search for start idx
        lo, hi = 0, len(self.data)
        # linear for now (fast enough < 100k) — fine for Phase1
        start_idx = 0
        for i, (c,_s) in enumerate(self.data):
            if c >= visible_start - int(1e-3*self.f_cpu):
                start_idx = max(0,i-1)
                break
        # draw grid & ruler
        self._draw_ruler(w, h, visible_start, visible_end)
        # draw channels
        y = 30
        for ch in self.channels:
            if not ch.get("enabled", True):
                continue
            ch_id = ch["id"]
            color = ch.get("color", "#00BFFF")
            label = ch.get("label") or f"CH{ch_id}"
            # channel label background
            self.create_rectangle(0, y-10, self.x_offset-2, y+14, fill="#252526", outline="#3C3C3C")
            self.create_text(6, y+2, anchor="w", text=label, fill=color, font=("Segoe UI", 9, "bold"))
            self.create_text(self.x_offset-6, y+2, anchor="e", text=f"{ch_id}", fill="#9E9E9E", font=("Segoe UI", 7))
            # waveform line for this channel
            # Build polyline: x = offset + (cycles - t0)/f_cpu / sec_per_px
            points = []
            # initial state before first edge?
            # We need state timeline: sample bits
            # For edge rendering, we step
            prev_c, prev_s = self.data[start_idx]
            prev_val = (prev_s >> ch_id) & 1
            prev_x = self.x_offset + (prev_c - self.t0)/self.f_cpu/self.sec_per_px
            # Start line at left edge
            y_high = y - 8
            y_low = y + 8
            cur_y = y_high if prev_val else y_low
            # iterate visible edges
            for idx in range(start_idx, len(self.data)):
                c,s = self.data[idx]
                if c < visible_start - 1000 and idx < len(self.data)-1:
                    # update prev without drawing
                    prev_val = (s >> ch_id) & 1
                    prev_c = c
                    continue
                if c > visible_end + 1000:
                    break
                x = self.x_offset + (c - self.t0)/self.f_cpu/self.sec_per_px
                # horizontal segment from prev_x to x at cur_y
                if x > prev_x+0.5:
                    self.create_line(prev_x, cur_y, x, cur_y, fill=color, width=1)
                # vertical edge if value changes
                val = (s >> ch_id) & 1
                if val != prev_val:
                    new_y = y_high if val else y_low
                    self.create_line(x, cur_y, x, new_y, fill=color, width=1)
                    cur_y = new_y
                    prev_val = val
                prev_x = x
            # extend to right edge
            if prev_x < w:
                self.create_line(prev_x, cur_y, w, cur_y, fill=color, width=1)
            y += self.y_per_ch
            if y > h - 20:
                break
        # trigger marker
        if self.trigger_cycle is not None:
            tx = self.x_offset + (self.trigger_cycle - self.t0)/self.f_cpu/self.sec_per_px
            if 0 <= tx <= w:
                self.create_line(tx, 0, tx, h, fill="#F44747", dash=(4,3), width=1)
                self.create_text(tx+4, 12, anchor="w", text="TRIG", fill="#F44747", font=("Segoe UI", 7, "bold"))
        # cursors
        for i,cyc in enumerate(self.cursors):
            x = self.x_offset + (cyc - self.t0)/self.f_cpu/self.sec_per_px
            if 0 <= x <= w:
                col = "#FFD700" if i==0 else "#FF8C00"
                self.create_line(x, 0, x, h, fill=col, dash=(2,2), width=1)
                self.create_text(x+4, 24 + i*12, anchor="w", text=f"C{i+1}", fill=col, font=("Segoe UI", 7, "bold"))
        # delta between cursors
        if len(self.cursors)==2:
            c0,c1 = self.cursors
            dt_cycles = abs(c1-c0)
            dt_s = dt_cycles / self.f_cpu
            if dt_s>0:
                freq = 1/dt_s if dt_s!=0 else 0
                txt = f"Δ {dt_s*1e6:.3f} µs  ({dt_s*1e3:.3f} ms)  {freq:.1f} Hz"
                self.create_rectangle(w-280, h-28, w-8, h-8, fill="#252526", outline="#3C3C3C")
                self.create_text(w-144, h-18, text=txt, fill="#D4D4D4", font=("Segoe UI", 8))

    def _draw_ruler(self, w, h, v0, v1):
        # time ruler at top
        self.create_rectangle(0,0,w,22, fill="#2D2D30", outline="#3C3C3C")
        span_s = (v1 - v0)/self.f_cpu if self.f_cpu else 1
        # choose tick step
        for exp in range(-9,2):
            step_s = 10**exp
            ticks = span_s/step_s
            if 4 <= ticks <= 12:
                break
        else:
            step_s = span_s/8
        # align to step
        t0_s = v0/self.f_cpu
        start_tick = math.floor(t0_s/step_s)*step_s
        for i in range(14):
            t = start_tick + i*step_s
            cyc = int(t*self.f_cpu)
            x = self.x_offset + (cyc - v0)/self.f_cpu/self.sec_per_px
            if 0 <= x <= w:
                self.create_line(x, 0, x, 22, fill="#3C3C3C")
                self.create_line(x, 22, x, 26, fill="#9E9E9E")
                # label
                if abs(t) < 1e-6:
                    label = f"{t*1e9:.0f} ns"
                elif abs(t) < 1e-3:
                    label = f"{t*1e6:.1f} µs"
                elif abs(t) < 1:
                    label = f"{t*1e3:.2f} ms"
                else:
                    label = f"{t:.3f} s"
                self.create_text(x+2, 11, anchor="w", text=label, fill="#9E9E9E", font=("Segoe UI", 7))
        # second labels for absolute? show small top right scale
        scale = f"{self.sec_per_px*1e6:.1f} µs/px"
        self.create_text(w-8, 11, anchor="e", text=scale, fill="#6A9955", font=("Consolas", 7))

    def set_zoom(self, sec_per_px: float):
        self.sec_per_px = max(1e-9, min(sec_per_px, 1e-2))
        self.redraw()

    def zoom_fit(self):
        if not self.data:
            return
        span = (self.data[-1][0] - self.data[0][0])/self.f_cpu
        w = self.winfo_width() or 1200
        usable = max(100, w - self.x_offset)
        self.sec_per_px = span/usable * 1.05
        self.t0 = self.data[0][0]
        self.redraw()
