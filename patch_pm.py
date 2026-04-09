import re

with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Update _open_position_internal to include initial_stop_loss
content = re.sub(
    r"stop_loss=stop_loss,\n                take_profit=take_profit,",
    r"stop_loss=stop_loss,\n                initial_stop_loss=stop_loss,\n                take_profit=take_profit,",
    content
)

# Update size_to_close rounding and bypass in close_position
content = re.sub(
    r"is_partial_close = size_to_close is not None and size_to_close < position.size",
    r"is_partial_close = size_to_close is not None and round(size_to_close, 4) < round(position.size, 4)\n            if size_to_close is not None:\n                size_to_close = round(size_to_close, 4)",
    content
)

# Update _update_trailing_stop functionality to support synchronous state updates and correct iteration
trailing_stop_stage_1_regex = r"        # ========================================================================\n        # AŞAMA 1: KISMI KÂR ALMA \(50% TP\) & BREAKEVEN KORUMASI\n        # ========================================================================\n        if position.should_take_partial_profit\(current_price\):\n(?:.*\n)*?            await event_bus.publish\(partial_event.to_event\(\)\)"

stage_1_replacement = """        # ========================================================================
        # AŞAMA 1: KISMI KÂR ALMA (R-Multiple) & BREAKEVEN KORUMASI
        # ========================================================================
        triggered_levels = position.get_triggered_tp_levels(current_price)
        if triggered_levels:
            total_percentage = sum(level.get("percentage", 0.0) for level in triggered_levels)
            if total_percentage > 0:
                size_to_close = round(position.size * total_percentage, 4)

                logger.info(
                    f"[RISK] 3 Aşamalı Kâr Koruma - AŞAMA 1 & 2: "
                    f"{position.symbol} {len(triggered_levels)} hedef vuruldu! "
                    f"Fiyat: ${current_price:.2f}, Kapanacak Miktar: {size_to_close}"
                )

                # Update take_profit_levels state synchronously
                new_tp_levels = []
                for level in position.take_profit_levels:
                    new_level = dict(level)
                    if new_level in triggered_levels:
                        new_level["hit"] = True
                    new_tp_levels.append(new_level)

                breakeven_price = position.entry_price

                # SENKRON STATE GÜNCELLEMESİ (Race Condition Koruması)
                position = dataclasses.replace(
                    position,
                    take_profit_levels=new_tp_levels,
                    stop_loss=breakeven_price,
                    partial_profit_taken=True,
                    breakeven_activated=True
                )
                self.positions[position.bot_id] = position

                # EVENT LOOP ASENKRON ÇAĞRI (State koruması sonrası fırlat)
                asyncio.create_task(
                    self.close_position(
                        bot_id=position.bot_id,
                        exit_price=current_price,
                        reason="partial_tp_hit",
                        size_to_close=size_to_close
                    )
                )"""

content = re.sub(trailing_stop_stage_1_regex, stage_1_replacement, content, flags=re.MULTILINE)

with open("core/trading/position_manager.py", "w") as f:
    f.write(content)
