import tkinter as tk
from tkinter import filedialog, messagebox

class GCodeLayerSwapper:
    def __init__(self, master):
        self.master = master
        master.title("G-code Layer Swapper")
        master.geometry("400x250")

        self.label = tk.Label(master, text="Open a G-code file to begin.")
        self.label.pack(pady=10)

        self.open_button = tk.Button(master, text="Open G-code File", command=self.open_file)
        self.open_button.pack(pady=5)

        self.save_button = tk.Button(master, text="Save Modified G-code", command=self.save_file, state=tk.DISABLED)
        self.save_button.pack(pady=5)

        self.status = tk.Label(master, text="Status: Waiting for file.", fg="blue")
        self.status.pack(pady=10)

        self.gcode_lines = []
        self.modified_lines = []

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("G-code Files", "*.gcode"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            # Remove all thumbnail blocks (any block starting with a line containing 'thumbnail' and 'begin', ending with a line containing 'thumbnail' and 'end')
            cleaned_lines = []
            in_thumbnail = False
            for line in lines:
                lower = line.lower()
                if 'thumbnail' in lower and 'begin' in lower:
                    in_thumbnail = True
                    continue
                if 'thumbnail' in lower and 'end' in lower:
                    in_thumbnail = False
                    continue
                if not in_thumbnail:
                    cleaned_lines.append(line)
            self.gcode_lines = cleaned_lines
            self.status.config(text="Status: File loaded. Choose layers to swap.")
            self.update_layer_options()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")

    def update_layer_options(self):
        # Find all layer indices using ;LAYER_CHANGE (case-insensitive)
        self.layer_indices = [i for i, line in enumerate(self.gcode_lines) if line.strip().lower().startswith(';layer_change')]
        num_layers = len(self.layer_indices)
        if num_layers < 2:
            self.status.config(text="Status: Not enough layers found.", fg="red")
            return
        # Add dropdowns for layer selection
        if hasattr(self, 'layer1_var'):
            self.layer1_menu.destroy()
            self.layer2_menu.destroy()
            self.swap_button.destroy()
        self.layer1_var = tk.IntVar(value=1)
        self.layer2_var = tk.IntVar(value=2)
        self.layer1_menu = tk.OptionMenu(self.master, self.layer1_var, *range(1, num_layers+1))
        self.layer2_menu = tk.OptionMenu(self.master, self.layer2_var, *range(1, num_layers+1))
        tk.Label(self.master, text="Paste this layer:").pack()
        self.layer2_menu.pack()
        tk.Label(self.master, text="Over this layer:").pack()
        self.layer1_menu.pack()
        self.swap_button = tk.Button(self.master, text="Swap Layers", command=self.gui_swap_layers)
        self.swap_button.pack(pady=5)

    def gui_swap_layers(self):
        layer1 = self.layer1_var.get()
        layer2 = self.layer2_var.get()
        if self.swap_layers(layer1, layer2):
            self.status.config(text=f"Status: Layer {layer2} pasted over Layer {layer1} (Z kept from {layer1}).", fg="green")
            self.save_button.config(state=tk.NORMAL)
        else:
            self.status.config(text="Status: Could not swap layers.", fg="red")

    def save_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".gcode", filetypes=[("G-code Files", "*.gcode"), ("All Files", "*.*")])
        if not file_path:
            return
        try:
            with open(file_path, 'w') as f:
                f.writelines(self.modified_lines)
            self.status.config(text="Status: File saved successfully.", fg="green")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def swap_layers(self, base_layer_num=1, paste_layer_num=2):
        # Find all layer indices using ;LAYER_CHANGE (case-insensitive)
        layer_indices = [i for i, line in enumerate(self.gcode_lines) if line.strip().lower().startswith(';layer_change')]
        if len(layer_indices) < max(base_layer_num, paste_layer_num):
            return False
        base_idx = layer_indices[base_layer_num-1]
        paste_idx = layer_indices[paste_layer_num-1]
        base_end = layer_indices[base_layer_num] if base_layer_num < len(layer_indices) else len(self.gcode_lines)
        paste_end = layer_indices[paste_layer_num] if paste_layer_num < len(layer_indices) else len(self.gcode_lines)
        base_layer = self.gcode_lines[base_idx:base_end]
        paste_layer = self.gcode_lines[paste_idx:paste_end]

        # Extract Z and HEIGHT from base_layer comments
        base_z = None
        base_height = None
        for line in base_layer:
            if line.strip().lower().startswith(';z:'):
                try:
                    base_z = float(line.strip().split(':')[1])
                except Exception:
                    pass
            if line.strip().lower().startswith(';height:'):
                try:
                    base_height = float(line.strip().split(':')[1])
                except Exception:
                    pass
        # Fallback: try to get Z from G1 commands if not found in comments
        if base_z is None:
            for line in base_layer:
                if line.strip().startswith('G1') and 'Z' in line:
                    for part in line.split():
                        if part.startswith('Z'):
                            try:
                                base_z = float(part[1:])
                            except Exception:
                                pass
                            break
                if base_z is not None:
                    break
        # Extract Z and HEIGHT from paste_layer comments
        paste_z = None
        paste_height = None
        for line in paste_layer:
            if line.strip().lower().startswith(';z:'):
                try:
                    paste_z = float(line.strip().split(':')[1])
                except Exception:
                    pass
            if line.strip().lower().startswith(';height:'):
                try:
                    paste_height = float(line.strip().split(':')[1])
                except Exception:
                    pass
        if paste_z is None:
            for line in paste_layer:
                if line.strip().startswith('G1') and 'Z' in line:
                    for part in line.split():
                        if part.startswith('Z'):
                            try:
                                paste_z = float(part[1:])
                            except Exception:
                                pass
                            break
                if paste_z is not None:
                    break
        # Calculate extrusion multiplier
        multiplier = 1.0
        if paste_height and base_height and paste_height != 0:
            multiplier = base_height / paste_height
        else:
            multiplier = 1.0
        # Replace Z and scale E in paste_layer, and update ;Z: and ;HEIGHT: comments
        new_paste_layer = []
        for line in paste_layer:
            lstripped = line.strip().lower()
            if lstripped.startswith(';z:') and base_z is not None:
                new_paste_layer.append(f';Z:{base_z}\n')
            elif lstripped.startswith(';height:') and base_height is not None:
                new_paste_layer.append(f';HEIGHT:{base_height}\n')
            elif line.strip().startswith('G1'):
                parts = line.split()
                new_parts = []
                for part in parts:
                    if part.startswith('Z') and base_z is not None:
                        new_parts.append(f'Z{base_z:.3f}')
                    elif part.startswith('E'):
                        try:
                            e_val = float(part[1:])
                            new_e = e_val * multiplier
                            new_parts.append(f'E{new_e:.5f}')
                        except ValueError:
                            new_parts.append(part)
                    else:
                        new_parts.append(part)
                new_paste_layer.append(' '.join(new_parts) + '\n')
            else:
                new_paste_layer.append(line)
        # Validation checks
        z_comment_ok = any(l.strip().lower() == f';z:{base_z}' for l in new_paste_layer if base_z is not None)
        height_comment_ok = any(l.strip().lower() == f';height:{base_height}' for l in new_paste_layer if base_height is not None)
        z_g1_ok = all((('Z' not in l) or (f'Z{base_z:.3f}' in l)) for l in new_paste_layer if l.strip().startswith('G1'))
        e_ok = True
        for orig, new in zip(paste_layer, new_paste_layer):
            if orig.strip().startswith('G1') and 'E' in orig and multiplier != 1.0:
                try:
                    orig_e = float([p[1:] for p in orig.split() if p.startswith('E')][0])
                    new_e = float([p[1:] for p in new.split() if p.startswith('E')][0])
                    if abs(new_e - orig_e * multiplier) > 1e-3:
                        e_ok = False
                        break
                except Exception:
                    continue
        # Rebuild file
        self.modified_lines = (
            self.gcode_lines[:base_idx] +
            new_paste_layer +
            self.gcode_lines[base_end:]
        )
        # Feedback
        msg = []
        if not z_comment_ok:
            msg.append("Z comment not updated correctly.")
        if not height_comment_ok:
            msg.append("HEIGHT comment not updated correctly.")
        if not z_g1_ok:
            msg.append("Not all G1 Z values were replaced correctly.")
        if not e_ok:
            msg.append("Not all E values were scaled correctly.")
        msg.append(f"Extrusion multiplier used: {multiplier:.5f}")
        if msg:
            messagebox.showinfo("Layer Swap Check", '\n'.join(msg))
        return z_comment_ok and height_comment_ok and z_g1_ok and e_ok

def main():
    root = tk.Tk()
    app = GCodeLayerSwapper(root)
    root.mainloop()

if __name__ == "__main__":
    main()
