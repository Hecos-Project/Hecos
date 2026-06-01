# Flows Module: Visual Automations

The **Flows** module of Hecos is the "orchestrator" of the system. It allows you to create automations, routines, and complex behaviors by chaining actions in a logical and sequential way.

You can create a flow using natural language (AI will write it for you), by drawing it via the **Visual Canvas** (Node Palette), or by writing it directly in **YAML** format.

---

## 1. How It Works (Key Concepts)

A Flow is composed of a series of **Nodes** (or *Steps*). Each node performs a single specific operation (for example: waiting 5 seconds, sending an email, reading a string).
- **Linear or Parallel Execution**: Nodes can be linked together. If *Node B* has a dependency (`depends_on`) on *Node A*, *Node B* will only be executed when *Node A* finishes successfully. Two nodes without dependencies will start in parallel!
- **Variable Sharing**: A node can save its result using the `output_as` option. For example, a node that checks the weather can save the result as `weather_data` and a subsequent node can read that data.
- **Triggers**: Every flow has a *trigger*. It can be manual (activated by a click), temporal (e.g. CRON "every Monday"), or based on a system event (e.g. receiving a message).

---

## 2. The YAML Format and the `key` Parameter

Behind the scenes (or in the integrated YAML editor), every flow is described in YAML format (an extremely readable and widespread standard). 
Unlike `JSON` (which uses rigid curly braces and quotes like `{"key": "value"}`), **YAML** uses simple indentation (spaces) and the syntax `key: value`.

### 💡 Solving the "key" misconception
When you are in the Node Editor (double-click on a node) and you read "Parameters (YAML)", or when you see a parameter called `key` in computer science, it simply means the **identifying name of that parameter**.

For example, if the system expects a YAML parameter structured like this:
```yaml
text: Good morning, are you ready to start the day?
sound: alarm_1
```
In this example:
- `text` is the **key** (the parameter's name/key).
- `Good morning, are you ready...` is the **value** (the assigned content/value).
You never explicitly write the word `{key: something}`, but you must use the correct names expected by the node (e.g., `text: ...`, `seconds: ...`).

---

## 3. Node Editor: The parameters explained

When you double-click a node on the Canvas, the **Node Editor** opens. Here is what the various fields are for:

- **Step ID (Unique)**: The unique identifier of this specific node (e.g. `notification_telegram`). It cannot contain spaces. It allows other nodes to reference _this specific node_ as a dependency.
- **Action**: The module to execute (e.g. `AUDIO__speak`, `LOGIC__delay`, `MAIL__send`). It determines what the node will do.
- **Parameters (YAML)**: Here you insert the node's configuration using YAML syntax. It's where you provide the machine with the data it needs. Example for `AUDIO__speak`: 
  ```yaml
  text: Hello Universe, I am Hecos.
  ```

  > [!IMPORTANT]
  > **Every node only accepts its own specific parameters!**
  > For instance, writing `text: Hello` works **only** for nodes that speak or write text (such as `AUDIO__speak` or `SYSTEM__chat_message`). If you put it inside a `LOGIC__delay` node, it will be ignored or throw an error, because the delay node strictly only understands the key `seconds: 10`.
  > To help you with this, whenever you drag a node to the canvas, **its required parameters will now appear automatically pre-filled** (with placeholder values like `<string>` or `0`). You just need to overwrite the placeholder with your actual data!

- **Output As (Variable)**: Many nodes generate a result (e.g. reading the time, a calculation result, an API response). If you provide a name here (e.g. `weather_value`), the result produced by this node becomes a **Variable**. Subsequent nodes can use this variable in their Parameters by writing `{{ weather_value }}` (using Jinja2 syntax).
- **Depends On (Comma-separated IDs)**: A comma-separated list of the **Step IDs** of all nodes that must finish _successfully_ before this node can even start (e.g. `step1, step_download`). It forces sequential execution.

---

## 4. Complete Node Catalog (Core Actions)

The Flows module natively integrates **15 actions**. In addition to these, Hecos automatically imports all actions from active system Plugins (such as the camera `WEBCAM__capture`, or mail `MAIL__send`). 

Here is the list of the 15 fundamental building blocks of Hecos Flows:

### 🛠️ LOGIC Category
The directors and traffic controllers: they delay, split, join, and evaluate decisions within the flow.
1. **LOGIC__delay**: Pauses the flow execution. _[Parameters: `seconds` (number)]_
2. **LOGIC__set_variable**: Explicitly assigns a value to a new variable in the flow. _[Parameters: `name`, `value`]_
3. **LOGIC__if_else**: Evaluates a Jinja2 mathematical/logical expression and branches the flow. _[Parameters: `condition`, `true_branch`, `false_branch`]_
4. **LOGIC__switch**: Executes different commands based on a specific condition. _[Parameters: `expression`, `branches`, `default`]_
5. **LOGIC__loop**: Iterates and processes a list repeatedly. _[Parameters: `over`, `as_var`, `body`]_
6. **LOGIC__template**: Generates or modifies a Jinja2 text by interpolating variables. _[Parameters: `template`, `output_as`]_
7. **LOGIC__and_gate**: Completes the flow *ONLY IF* several conditions are all simultaneously true. _[Parameters: `conditions`, `on_success`, `on_fail`]_
8. **LOGIC__or_gate**: Executes if *AT LEAST ONE* condition is true. _[Parameters: `conditions`, `on_success`, `on_fail`]_
9. **LOGIC__http_request**: Calls external APIs or internet services and saves the returned JSON response in a variable. _[Parameters: `method`, `url`, `headers`, `body`, `output_as`]_

### ⏰ TRIGGER Category
Indicates how this automation will "come to life" automatically over time (these fields modify the flow root, not standard blocks).
10. **TRIGGER__cron**: The flow starts automatically at scheduled times using standard UNIX Cron (e.g. `0 7 * * *`). _[Parameters: `expression`]_
11. **TRIGGER__interval**: The flow repeats constantly every "N" time units (e.g. every 10 `minutes`). _[Parameters: `every`, `unit`]_
12. **TRIGGER__manual**: This flow is configured strictly to run manually via a "Play" button. No hidden background execution. _[No Parameters]_

### 🔊 AUDIO Category
Basic multimedia events played on the primary device.
13. **AUDIO__speak**: Activates the Text-to-Speech synthesizer to make the AI speak directly. _[Parameters: `text`]_
14. **AUDIO__play_alarm**: Loops one of the pre-stored ringtones or alarms inside Hecos. _[Parameters: `sound`]_

### 💬 SYSTEM Category
Interacts directly with the core AI memory and interfaces.
15. **SYSTEM__chat_message**: Saves and displays a text message into the classic Hecos Chat history, as if the assistant were writing to you. _[Parameters: `text`]_

### 🧠 AI Category
Allows Flows to interact **bidirectionally** with the AI brain — not just to write static messages, but to send real prompts to the AI and capture its response as a variable.
16. **AI__prompt**: Sends a text prompt to the full Hecos AgentExecutor (the complete brain, including routing, plugins, and tool calls). The flow **blocks** until the AI has finished responding; the response text is then returned and can be stored using `output_as`. _[Parameters: `prompt` (string), `save_to_chat` (bool, default: true)]_
   > Note: with `save_to_chat: true`, the prompt+response pair is written to the chat history as `[Flow] prompt text` (user role) and the AI reply (assistant role), so you can always review what the flow "thought".

---

## 5. Practical Complete Examples

Below are three examples of complete YAML flows, perfect for analyzing how nodes behave with variables (`output_as`), dependencies, and in parallel.

### Example 1: Morning Routine with Dynamic Variables
This flow introduces parameter chaining: Hecos acquires the current time, storing it in the variable `current_time` by utilizing `output_as`, and then recites it in the next step by interpolating it within the curly braces `{{ current_time }}`.

```yaml
name: Advanced Morning Routine
trigger:
  type: manual
pipeline:
  - id: step_alarm
    action: AUDIO__play_alarm
    params:
      sound: gentle_wake

  - id: step_pause
    action: LOGIC__delay
    params:
      seconds: 5
    depends_on:
      - step_alarm

  - id: get_current_time
    action: EXECUTOR__get_time
    # We save the output in the variable 'current_time'
    output_as: current_time
    depends_on:
      - step_pause

  - id: step_greeting
    action: AUDIO__speak
    params:
      # We use the output generated by the "get_current_time" block
      text: "Good morning! It is currently {{ current_time }}, you need to get up."
    depends_on:
      - get_current_time
```

### Example 2: Multiple Home Security Alert (Parallelism)
In this flow we will see **parallelism in action**. The two blocks `notify_voice` and `send_email_alert` share the exact same dependency (`wait_for_arming`). This means that, once the LOGIC__delay is over, Hecos will execute both notifications simultaneously, performing true asynchronous multitasking!

```yaml
name: Multiple Security Alert
trigger:
  type: manual
pipeline:
  - id: wait_for_arming
    action: LOGIC__delay
    params:
      seconds: 30

  - id: notify_voice
    action: AUDIO__speak
    params:
      text: "Warning, the automatic security system has been initiated and armed."
    depends_on:
      - wait_for_arming

  - id: send_email_alert
    action: MAIL__send
    params:
      to: admin@myhouse.com
      subject: "Hecos Alarm"
      body: "We are notifying you that the security system has been armed."
    depends_on:
      - wait_for_arming
```

### Example 3: Device Control with API and Sequential Events
This block calls the servers of an API and, only after a pause, produces a closure. Imagine this as a smart home macro connecting to Philips Hue or Home Assistant!

```yaml
name: Smart Coffee Machine
trigger:
  type: interval
  every: 6
  unit: hours
pipeline:
  - id: call_coffee_api
    action: LOGIC__http_request
    params:
      method: "POST"
      url: "http://192.168.1.50/api/coffee_maker/start"
      body:
        mode: "espresso_macchiato"

  - id: announce_start
    action: AUDIO__speak
    params:
      text: "The operation to make a fantastic espresso is underway."
    depends_on:
      - call_coffee_api

  - id: wait_brewing
    action: LOGIC__delay
    params:
      seconds: 40
    depends_on:
      - announce_start

  - id: announce_ready
    action: AUDIO__speak
    params:
      text: "Your highly scented coffee is ready."
    depends_on:
      - wait_brewing
```

> Note: All these example files faithfully represent textually the exact same structure that the system manages when you connect, disconnect, or write parameters entirely inside your easy visual Canvas!

---

## 6. Advanced Examples: Real & Bizarre Scenarios

These three examples demonstrate the true potential of Flows: conditional algorithms, timed procedural chains, and sci-fi style integrations. Use them as inspiration and modify the parameters to suit your own environment.

---

### 🧮 Example A — The Bitcoin Watchdog Algorithm
*Scenario: Every 10 minutes, Hecos queries the CoinGecko API, retrieves the current price of Bitcoin, and makes a decision: if the price crashes below €60,000, it yells out loud and sends you an urgent email; if it surpasses €100,000, it celebrates with you in chat. Otherwise, it silently logs the price.*

This is the purest form of an algorithm: data input → processing → conditional action.

```yaml
name: Bitcoin Watchdog Algorithm
trigger:
  type: interval
  every: 10
  unit: minutes
pipeline:
  # STEP 1: Call the public CoinGecko API (zero API key, zero cost)
  - id: get_bitcoin_price
    action: LOGIC__http_request
    params:
      method: GET
      url: "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=eur"
      output_as: api_response

  # STEP 2: Extract the raw numeric value from the JSON response
  - id: extract_price
    action: LOGIC__template
    params:
      template: "{{ api_response.bitcoin.eur }}"
      output_as: btc_price
    depends_on:
      - get_bitcoin_price

  # STEP 3: Build a readable message
  - id: format_message
    action: LOGIC__template
    params:
      template: "Bitcoin is currently worth {{ btc_price }} euros."
      output_as: price_summary
    depends_on:
      - extract_price

  # STEP 4: BRANCHING — Evaluate the price using if_else
  - id: check_crash
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} < 60000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "RED ALERT! Bitcoin just crashed to {{ btc_price }} euros! Open Coinbase NOW!"
      false_branch:
        action: SYSTEM__chat_message
        params:
          text: "📊 {{ price_summary }} — situation normal."
    depends_on:
      - format_message

  # STEP 5 (parallel to 4): Check the MOON hypothesis
  - id: check_moon
    action: LOGIC__if_else
    params:
      condition: "{{ btc_price | int }} > 100000"
      true_branch:
        action: AUDIO__speak
        params:
          text: "AAAA! We surpassed one hundred thousand euros! We are on Mars! 🚀"
      false_branch:
        action: LOGIC__delay
        params:
          seconds: 1  # no action, symbolic wait
    depends_on:
      - format_message

  # STEP 6: If we are crashing, also send an urgent email
  - id: emergency_mail
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "⚠️ Bitcoin Crash Alert — Hecos Watchdog"
      body: "{{ price_summary }} — The price is below the critical threshold. Check it immediately."
    depends_on:
      - check_crash
```

---

### 🍮 Example B — The Robotic Chef: Step-by-Step Chocolate Soufflé
*Scenario: An interactive recipe that replaces your phone's timer with Hecos vocally guiding you step-by-step, with precise countdowns, alarms, and chat reminders for every critical phase. Follow it and your soufflé will be perfect.*

This is the shape of a procedural recipe-flow: pure sequential pipelining with surgical delays.

```yaml
name: Chocolate Soufflé Recipe
trigger:
  type: manual
pipeline:
  # PHASE 1 - Preparation: announcement and setup
  - id: begin_recipe
    action: AUDIO__speak
    params:
      text: "Welcome to the chocolate soufflé recipe. Prepare 200 grams of dark chocolate, 4 eggs, and some butter."

  - id: set_oven_temp
    action: SYSTEM__chat_message
    params:
      text: "🍫 **RECIPE ACTIVE** — Preheat the oven to 190°C. Butter and sugar 4 soufflé ramekins."
    depends_on:
      - begin_recipe

  # PHASE 2 - Melting the chocolate (7 minutes bain-marie)
  - id: announce_melt
    action: AUDIO__speak
    params:
      text: "Now melt the chocolate using a bain-marie. I will notify you in 7 minutes."
    depends_on:
      - set_oven_temp

  - id: wait_melt
    action: LOGIC__delay
    params:
      seconds: 420  # 7 minutes
    depends_on:
      - announce_melt

  - id: alarm_melt_done
    action: AUDIO__play_alarm
    params:
      sound: chime_success
    depends_on:
      - wait_melt

  - id: say_melt_done
    action: AUDIO__speak
    params:
      text: "The chocolate is ready. Remove from heat and add the butter. Then separate the yolks from the egg whites."
    depends_on:
      - alarm_melt_done

  # PHASE 3 - Whipping the egg whites (estimated 4 mins with electric whisk)
  - id: announce_whip
    action: AUDIO__speak
    params:
      text: "Start whipping the egg whites until stiff peaks form. I will alert you in 4 minutes when they are ready."
    depends_on:
      - say_melt_done

  - id: wait_whip
    action: LOGIC__delay
    params:
      seconds: 240  # 4 minutes
    depends_on:
      - announce_whip

  - id: say_whip_done
    action: AUDIO__speak
    params:
      text: "Egg whites are ready! Gently fold them into the chocolate from bottom to top. Then fill the ramekins three-quarters full."
    depends_on:
      - wait_whip

  # PHASE 4 - Baking (EXACTLY 12 minutes, do not open the oven!)
  - id: announce_baking
    action: AUDIO__speak
    params:
      text: "Put them in the oven. Warning: take them out in exactly 12 minutes. DO NOT open the oven before then — they will explode!"
    depends_on:
      - say_whip_done

  - id: chat_baking_warning
    action: SYSTEM__chat_message
    params:
      text: "⏱️ **Soufflé baking started** — Do not open the oven! Timer: 12 minutes. End of baking coming soon."
    depends_on:
      - say_whip_done

  - id: wait_baking
    action: LOGIC__delay
    params:
      seconds: 720  # exactly 12 minutes
    depends_on:
      - announce_baking

  - id: final_alarm
    action: AUDIO__play_alarm
    params:
      sound: alarm_urgent
    depends_on:
      - wait_baking

  - id: final_announcement
    action: AUDIO__speak
    params:
      text: "NOW! Take the soufflés out of the oven RIGHT NOW and serve them immediately! Enjoy your meal!"
    depends_on:
      - final_alarm

  - id: final_chat
    action: SYSTEM__chat_message
    params:
      text: "✅ **Soufflé complete!** Serve within 60 seconds of baking. Bon appétit, chef!"
    depends_on:
      - final_alarm
```

---

### 🤖 Example C — The Midnight Sentinel (Home Sci-Fi)
*Scenario: Every night at midnight, Hecos wakes up like a silent robotic guardian. It queries three smart-home APIs (smart lock, surveillance camera, temperature sensor), validates the results using a logical AND-gate, and only if everything is fine does it send a report in chat. If something is anomalous, it triggers a voice alarm + a custom-formatted alert email. A true YAML-programmed security system.*

```yaml
name: Midnight Home Sentinel
trigger:
  type: cron
  expression: "0 0 * * *"  # every night at 00:00
pipeline:
  # PHASE 1 - Silent announcement in chat (no audio - it's night!)
  - id: begin_patrol
    action: SYSTEM__chat_message
    params:
      text: "🌙 **Night Patrol Started** — Hecos is checking the status of the house..."

  # PHASE 2 (parallel) - Query 3 smart-home APIs simultaneously
  - id: check_lock
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.10/api/smart_lock/status"
      output_as: lock_status
    depends_on:
      - begin_patrol

  - id: check_camera
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.11/api/camera/motion_detected"
      output_as: camera_status
    depends_on:
      - begin_patrol

  - id: check_temperature
    action: LOGIC__http_request
    params:
      method: GET
      url: "http://192.168.1.12/api/thermostat/current_temp"
      output_as: temp_data
    depends_on:
      - begin_patrol

  # PHASE 3 - AND GATE: proceed only if lock is locked and no motion
  - id: security_gate
    action: LOGIC__and_gate
    params:
      conditions:
        - "{{ lock_status.locked == true }}"
        - "{{ camera_status.motion == false }}"
      on_success:
        action: SYSTEM__chat_message
        params:
          text: "✅ **House SECURE** — Lock: locked | Camera: no motion | Temp: {{ temp_data.celsius }}°C"
      on_fail:
        action: AUDIO__speak
        params:
          text: "WARNING! The night patrol has detected an anomaly! Check the house immediately!"
    depends_on:
      - check_lock
      - check_camera
      - check_temperature

  # PHASE 4 - Compose a formatted report and send via mail
  - id: compose_report
    action: LOGIC__template
    params:
      template: |
        HECOS NIGHT REPORT — Midnight
        Lock: {{ lock_status.locked | ternary('LOCKED', 'UNLOCKED!!') }}
        Camera Motion: {{ camera_status.motion | ternary('DETECTED!!', 'None') }}
        Indoor Temp: {{ temp_data.celsius }}°C
        Overall Status: {{ 'ALL CLEAR' if lock_status.locked and not camera_status.motion else 'ANOMALY DETECTED' }}
      output_as: night_report
    depends_on:
      - security_gate

  - id: send_night_report
    action: MAIL__send
    params:
      to: me@myemail.com
      subject: "🌙 Hecos Night Report — House Monitored"
      body: "{{ night_report }}"
    depends_on:
      - compose_report
```

> 💡 **Bonus challenge**: connect this flow to the `WEBCAM__capture` action to attach an actual picture from the internal camera to the midnight report. Just add a node between `check_camera` and `compose_report`!
