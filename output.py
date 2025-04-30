import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import re

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

    # flat 10% liability per golfer
    cap_liability = 0.10 * bank
    candidates = []

    # parse each pasted line
    for line in lines:
        if "|" not in line:
            continue
        name, rest = line.split("|", 1)
        name = name.strip()
        rest = rest.strip()

        # extract Model% and LiveOdds
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

        # flat-only stake: liability = 10% of bank
        stake     = cap_liability / (live_odds - 1)
        liability = cap_liability

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
    output_txt.insert(tk.END, f"Flat liability per golfer: 10% of bank (£{cap_liability:.2f})\n\n")

    if not candidates:
        output_txt.insert(tk.END, "No positive-EV lays found.\n")
    else:
        output_txt.insert(tk.END, "Name       | Odds  | LayEV   | Stake    | Liab\n")
        output_txt.insert(tk.END, "------------------------------------------------\n")
        for c in candidates:
            output_txt.insert(
                tk.END,
                f"{c['name']:<10} | {c['odds']:>5.2f} | {c['ev_lay']:+6.3f} | "
                f"£{c['stake']:>6.2f} | £{c['liability']:>6.2f}\n"
            )
        output_txt.insert(tk.END, "------------------------------------------------\n")

# Build GUI
root = tk.Tk()
root.title("Odds Apex - Lay Optimizer")

tk.Label(root, text="Paste your model output here:")\
    .grid(row=0, column=0, sticky="w", padx=4, pady=4)
input_txt = ScrolledText(root, width=80, height=8)
input_txt.grid(row=1, column=0, columnspan=2, padx=4)

tk.Label(root, text="Account balance (£):")\
    .grid(row=2, column=0, sticky="w", padx=4, pady=(10,2))
balance_entry = tk.Entry(root)
balance_entry.grid(row=2, column=1, sticky="w", padx=4)

tk.Button(root, text="Calculate Lays", command=calculate_lays)\
    .grid(row=3, column=0, columnspan=2, pady=8)

tk.Label(root, text="Recommendations:")\
    .grid(row=4, column=0, sticky="w", padx=4, pady=(10,2))
output_txt = ScrolledText(root, width=80, height=12)
output_txt.grid(row=5, column=0, columnspan=2, padx=4, pady=(0,8))

root.mainloop()
