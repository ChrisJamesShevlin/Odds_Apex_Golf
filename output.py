import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

# Each lay's max liability is 10% of bankroll
def calculate_lays():
    output_txt.delete("1.0", tk.END)
    lines = input_txt.get("1.0", tk.END).strip().splitlines()

    # read & validate bankroll
    try:
        bank = float(balance_entry.get())
        if bank <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Input Error", "Please enter a positive number for your account balance.")
        return

    cap_liability = 0.10 * bank  # per golfer cap
    candidates = []

    # parse each pasted line
    for line in lines:
        if "|" not in line:
            continue
        name, rest = line.split("|", 1)
        name = name.strip()
        rest = rest.strip()

        # extract Model% (or Model:) and LiveOdds
        m_mod = re.search(r"Model[:%]?\s*([0-9]+(?:\.[0-9]+)?)%", rest)
        m_od  = re.search(r"LiveOdds[:]?[\s]*([0-9]+(?:\.[0-9]+)?)", rest)
        if not (m_mod and m_od):
            continue

        p_model   = float(m_mod.group(1)) / 100.0
        live_odds = float(m_od.group(1))
        if live_odds <= 1:
            continue

        # compute lay EV
        ev_back = p_model * (live_odds - 1) - (1 - p_model)
        ev_lay  = -ev_back
        if ev_lay <= 0:
            continue

        # full Kelly fraction for lay and 25% Kelly
        f_full = ev_lay / (live_odds - 1)
        f_25   = max(0, f_full) * 0.25
        stake     = f_25 * bank
        liability = stake * (live_odds - 1)

        # enforce per-golfer liability cap
        if liability > cap_liability:
            liability = cap_liability
            stake = liability / (live_odds - 1)

        candidates.append({
            "name":      name,
            "odds":      live_odds,
            "ev_lay":    ev_lay,
            "stake":     stake,
            "liability": liability
        })

    # sort candidates by EV descending
    candidates.sort(key=lambda c: c["ev_lay"], reverse=True)

    # output header
    output_txt.insert(tk.END, f"Bankroll: £{bank:.2f}\n")
    output_txt.insert(tk.END, f"Max liability per golfer (10%): £{cap_liability:.2f}\n\n")

    if not candidates:
        output_txt.insert(tk.END, "No positive-EV lays found.\n")
    else:
        output_txt.insert(tk.END, "Recommendations (25% Kelly, per golfer cap):\n")
        output_txt.insert(tk.END, "---------------------------------------------------------\n")
        for c in candidates:
            output_txt.insert(tk.END,
                f"{c['name']:<12} | Odds: {c['odds']:>5.2f} | "
                f"LayEV: {c['ev_lay']:+.3f} | "
                f"Stake: £{c['stake']:>6.2f} | "
                f"Liab: £{c['liability']:>6.2f}\n"
            )
        output_txt.insert(tk.END, "---------------------------------------------------------\n")

# Build GUI
tk_root = tk.Tk()
tk_root.title("Odds Apex - Golf Output")

# Input
tk.Label(tk_root, text="Paste your model output here:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
input_txt = ScrolledText(tk_root, width=80, height=8)
input_txt.grid(row=1, column=0, padx=4)

# Bankroll entry
tk.Label(tk_root, text="Account balance (£):").grid(row=2, column=0, sticky="w", padx=4, pady=(10,2))
balance_entry = tk.Entry(tk_root)
balance_entry.grid(row=3, column=0, sticky="w", padx=4)

# Calculate button
calc_btn = tk.Button(tk_root, text="Calculate Lays", command=calculate_lays)
calc_btn.grid(row=4, column=0, sticky="w", padx=4, pady=8)

# Output
tk.Label(tk_root, text="Recommendations:").grid(row=5, column=0, sticky="w", padx=4, pady=(10,2))
output_txt = ScrolledText(tk_root, width=80, height=12)
output_txt.grid(row=6, column=0, padx=4, pady=(0,8))

# Launch
tk_root.mainloop()
