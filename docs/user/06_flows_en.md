# Flows Module: Visual Automations

The **Flows** module of Hecos is the "orchestrator" of the system. It allows you to create automations, routines, and complex behaviors by chaining actions in a logical and sequential way.

![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main/////010_Hecos_Flows_001.png?raw=true)

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

![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main//////011_Hecos_Flows_002.png?raw=true)


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


![Hecos - Flows Automations](https://github.com/Hecos-Project/Hecos-Assets/blob/main///////012_Hecos_Flows_003.png?raw=true)



  Here are 3 complete practical examples to help you master how to pass data between nodes:

  **Example 1: Passing Text (Weather Tracking)**
  Imagine having an API node that fetches the weather and you want it spoken aloud. 
  1. On the `LOGIC__http_request` node, set *Output As* to `weather_result`.
  2. Chain a Speech Synthesizer node (`AUDIO__speak`) right after it.
  3. Double click on the speech node to open its Parameters. In the *text* field, write exactly: `Attention, the forecast says: {{ weather_result }}`.
  When the flow runs, Hecos won't read the curly braces: it will instantly replace them with the live weather data! This is how you pass data.

  **Example 2: Logical and Mathematical Operations**
  Variables can carry numbers, perfect for establishing alternative branches.
  1. Add an action that extracts the current time and name the *Output As* `current_time`.
  2. Connect this node to a `LOGIC__if_else` crossroads block.
  3. Inside the *condition* parameter, write: `{{ current_time.hour }} > 12`. 
  The expression is evaluated mathematically. Now the system knows to take the *True* path only during the afternoon, seamlessly branching the automation using data generated just milliseconds before.

  **Example 3: Multiple Chaining (AI Prompting)**
  Nothing stops you from combining and mixing loads of curly braces in the same parameter box!
  1. Assume you already piped out a result called `user_name` and another called `house_status`.
  2. Drop a powerful `AI__prompt` "Brain" node onto the canvas.
  3. In the free *prompt* parameter, write: `"Dear agent, make a sarcastic report about the house status: {{ house_status }} and greet my boss, {{ user_name }}."`
  4. Now set the AI node's *Output As* to `finished_translation`. You can chain this even further into an email by just typing `{{ finished_translation }}` as the `MAIL__send` body!

- **Depends On (Comma-separated IDs)**: A comma-separated list of the **Step IDs** of all nodes that must finish _successfully_ before this node can even start (e.g. `step1, step_download`). It forces sequential execution.

---

## 4. Complete Node Catalog (Core Actions)

The Flows module natively integrates **19 actions**. In addition to these, Hecos automatically imports all actions from active system Plugins (such as the camera `WEBCAM__capture`, or mail `MAIL__send`). 

Here is the list of the fundamental building blocks of Hecos Flows:

### 🛠️ LOGIC Category
The directors and traffic controllers: they delay, split, join, and evaluate decisions within the flow.

---

#### 1. `LOGIC__delay` — Timed Pause
Pauses flow execution for a precise number of seconds before moving on to the next node.

| Parameter | Type | Description |
|-----------|------|-------------|
| `seconds` | number | Seconds to wait (e.g. `5`, `30`, `120`) |

```yaml
- id: pause_5_seconds
  action: LOGIC__delay
  params:
    seconds: 5
```

---

#### 2. `LOGIC__set_variable` — Set a Variable
Creates or overwrites a variable in the flow context with a static or dynamic (Jinja2) value. Unlike `output_as`, this variable is available to **all** subsequent nodes without explicit dependencies.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | string | Name of the variable to create (e.g. `user_name`) |
| `value` | any | Value to assign. Can contain `{{ variables }}` |

```yaml
- id: set_threshold
  action: LOGIC__set_variable
  params:
    name: temperature_threshold
    value: 25

- id: personalized_greeting
  action: LOGIC__set_variable
  params:
    name: message
    value: "Good morning {{ user_name }}, the threshold is {{ temperature_threshold }}°C"
```

---

#### 3. `LOGIC__if_else` — Conditional Fork _(most used!)_
Evaluates a Jinja2 logical/mathematical expression and **executes only one** of two branches: `true_branch` if the condition is true, `false_branch` if it is false.

> [!IMPORTANT]
> **Why does the node seem to run both branches?** If you leave `condition` empty or unfilled, the engine defaults to `false` and always picks `false_branch`. If both `true_branch` and `false_branch` are empty, nothing happens. Make sure you fill in all three fields!

| Parameter | Type | Description |
|-----------|------|-------------|
| `condition` | Jinja2 string | The expression to evaluate. **Must return true or false.** Use `{{ variable }}` for dynamic data. |
| `true_branch` | dict | The node to execute if the condition is **true**. Contains `action` and `params`. |
| `false_branch` | dict | The node to execute if the condition is **false**. Contains `action` and `params`. |

**Valid condition examples:**
```yaml
# Numeric comparison
condition: "{{ temperature | int }} > 30"

# String comparison
condition: "{{ status }} == 'active'"

# Boolean value directly from an API
condition: "{{ sensor.detected == true }}"

# Time comparison (dot notation for dict fields)
condition: "{{ current_time.hour | int }} > 12"
```

**Full example — Smart Thermostat:**
```yaml
- id: check_temperature
  action: LOGIC__if_else
  params:
    condition: "{{ current_temp | int }} > 28"
    true_branch:
      action: AUDIO__speak
      params:
        text: "It's hot! Temperature is {{ current_temp }} degrees. Turning on the AC."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "Temperature is normal: {{ current_temp }}°C."
  depends_on:
    - read_sensor
```

**Example with multiple actions in one branch (list):**
```yaml
- id: check_alarm
  action: LOGIC__if_else
  params:
    condition: "{{ motion_detected == true }}"
    true_branch:
      - action: AUDIO__speak
        params:
          text: "Warning! Motion detected!"
      - action: AUDIO__play_alarm
        params:
          sound: alarm_urgent
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "No motion. House is safe."
```

---

#### 4. `LOGIC__switch` — Multi-Way Selector
Advanced routing: evaluates an expression and uses its result as a **key** to choose which action to run out of many possibilities. Like an if/else with many branches.

| Parameter | Type | Description |
|-----------|------|-------------|
| `expression` | Jinja2 string | The expression whose result (string) is used as a lookup key |
| `branches` | dict | Map of `key: action` — each key corresponds to a possible expression value |
| `default` | dict | Fallback action if no key matches (optional) |

```yaml
- id: choose_greeting
  action: LOGIC__switch
  params:
    expression: "{{ time_of_day }}"
    branches:
      morning:
        action: AUDIO__speak
        params:
          text: "Good morning! Ready for a productive day?"
      afternoon:
        action: AUDIO__speak
        params:
          text: "Good afternoon! How is work going?"
      evening:
        action: AUDIO__speak
        params:
          text: "Good evening! Time to relax."
    default:
      action: AUDIO__speak
      params:
        text: "Hello! I'm not sure what time it is, but I'm here for you."
```

---

#### 5. `LOGIC__loop` — Loop Over a List
Iterates over each element in a list (stored in a variable) and runs an action for each one.

| Parameter | Type | Description |
|-----------|------|-------------|
| `over` | string | The name of the variable holding the list (e.g. `recipients`) |
| `as_var` | string | The temporary variable name for the current element (e.g. `email`) |
| `body` | dict | The action to run for each element. Use `{{ as_var }}` in params. |

```yaml
# Example: log a message for each room in the list
- id: init_list
  action: LOGIC__set_variable
  params:
    name: rooms
    value:
      - kitchen
      - living_room
      - bedroom

- id: check_each_room
  action: LOGIC__loop
  params:
    over: rooms
    as_var: room
    body:
      action: SYSTEM__chat_message
      params:
        text: "Check complete for: {{ room }}"
  depends_on:
    - init_list
```

---

#### 6. `LOGIC__template` — Jinja2 Text Builder
Renders a Jinja2 template by interpolating variables and saves the result as a new variable. Perfect for composing complex messages before sending them.

| Parameter | Type | Description |
|-----------|------|-------------|
| `template` | Jinja2 string | The text with variables to substitute (use `{{ variable }}`) |
| `output_as` | string | Name of the variable in which to store the final result |

```yaml
- id: compose_report
  action: LOGIC__template
  params:
    template: |
      Report for {{ today }}
      Temperature: {{ temp }}°C
      Status: {{ 'OK' if temp|int < 30 else 'CRITICAL' }}
    output_as: report_text
  depends_on:
    - read_data

- id: send_report
  action: MAIL__send
  params:
    to: admin@myhouse.com
    subject: Daily Report
    body: "{{ report_text }}"
  depends_on:
    - compose_report
```

---

#### 7. `LOGIC__and_gate` — AND Gate (all conditions)
Runs `on_success` **only if ALL** conditions in the list are true. If even one is false, runs `on_fail`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `conditions` | list of strings | List of Jinja2 expressions to evaluate. All must be true. |
| `on_success` | dict | Action to run if **all** conditions pass |
| `on_fail` | dict | Action to run if **at least one** condition fails (optional) |

```yaml
- id: check_security
  action: LOGIC__and_gate
  params:
    conditions:
      - "{{ lock.locked == true }}"
      - "{{ alarm.active == true }}"
      - "{{ temperature.celsius | int }} < 40"
    on_success:
      action: SYSTEM__chat_message
      params:
        text: "✅ House secure: lock closed, alarm active, temperature OK."
    on_fail:
      action: AUDIO__speak
      params:
        text: "Warning! At least one security condition is not met!"
  depends_on:
    - check_lock
    - check_alarm
    - check_temp
```

---

#### 8. `LOGIC__or_gate` — OR Gate (at least one condition)
Runs `on_success` if **AT LEAST ONE** of the conditions is true. Runs `on_fail` only if **none** of the conditions are true.

| Parameter | Type | Description |
|-----------|------|-------------|
| `conditions` | list of strings | List of Jinja2 expressions. Just one needs to be true. |
| `on_success` | dict | Action if at least one condition is true |
| `on_fail` | dict | Action if no condition is true (optional) |

```yaml
- id: notify_if_anomaly
  action: LOGIC__or_gate
  params:
    conditions:
      - "{{ cpu_usage | int }} > 90"
      - "{{ ram_usage | int }} > 85"
      - "{{ disk_full == true }}"
    on_success:
      action: AUDIO__speak
      params:
        text: "Warning: the system is running out of resources! Check immediately."
    on_fail:
      action: SYSTEM__chat_message
      params:
        text: "System healthy. No anomalies detected."
```

---

#### 9. `LOGIC__http_request` — API/Web Call
Makes an HTTP request to any URL and saves the JSON (or text) response as a variable. This is the node that connects Hecos to the outside world.

| Parameter | Type | Description |
|-----------|------|-------------|
| `method` | string | HTTP method: `GET`, `POST`, `PUT`, `DELETE` |
| `url` | string | Target URL. Supports Jinja2 (e.g. `https://api.example.com/{{ id }}`) |
| `headers` | dict | Optional headers (e.g. `Authorization: Bearer TOKEN`) |
| `body` | dict or string | Request body for POST/PUT (optional) |
| `output_as` | string | Variable name to store the parsed JSON response |

```yaml
# Simple GET — current weather
- id: fetch_weather
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.open-meteo.com/v1/forecast?latitude=51.5&longitude=-0.1&current_weather=true"
    output_as: weather_data

# Read the result in the next node
- id: announce_weather
  action: AUDIO__speak
  params:
    text: "Current temperature in London is {{ weather_data.current_weather.temperature }} degrees."
  depends_on:
    - fetch_weather

# POST with authentication — webhook notification
- id: notify_webhook
  action: LOGIC__http_request
  params:
    method: POST
    url: "https://hooks.example.com/notify"
    headers:
      Authorization: "Bearer my-secret-token"
      Content-Type: "application/json"
    body:
      event: "flow_completed"
      message: "{{ result }}"
    output_as: webhook_response
```

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

### 🧭 CONTROL Category
Nodes for controlling the execution flow.

#### 17. `CONTROL__start` — Flow Entry Point
Acts as the mandatory entry point for flow execution. Any node not connected (directly or indirectly via `depends_on` dependencies) to a `CONTROL__start` node will not execute. This prevents accidental execution of floating or isolated branches.

If a flow contains one or more `CONTROL__start` nodes, execution will begin exclusively from them. If the `CONTROL__start` node is disabled (using `disable_mode: stop`), execution of the entire flow will fail immediately.

| Parameter | Type | Description |
|-----------|------|-------------|
| `priority` | integer | Startup priority order (default: `0`). Start nodes with lower values run first (e.g., `0` before `1`). |

**Example 1: Simple Linear Startup**
A basic flow that starts explicitly from the Start node and speaks a greeting.
```yaml
- id: start_1
  action: CONTROL__start
  params:
    priority: 0

- id: notify_hello
  action: AUDIO__speak
  params:
    text: "System ready and started."
  depends_on:
    - start_1
```

**Example 2: Ordered Execution of Multiple Branches**
Two start nodes executed in temporal sequence using priority. `initialize` runs first, followed by `start_operation`.
```yaml
- id: initialize
  action: CONTROL__start
  params:
    priority: 0

- id: set_var
  action: LOGIC__set_variable
  params:
    name: system_state
    value: "ready"
  depends_on:
    - initialize

- id: start_operation
  action: CONTROL__start
  params:
    priority: 1

- id: run_task
  action: SYSTEM__chat_message
  params:
    text: "Execution started. System state: {{ system_state }}"
  depends_on:
    - start_operation
```

**Example 3: Startup Security Verification**
At startup, the flow verifies a condition before proceeding, stopping if necessary.
```yaml
- id: start_security
  action: CONTROL__start
  params:
    priority: 0

- id: check_connection
  action: LOGIC__http_request
  params:
    method: GET
    url: "https://api.ipify.org?format=json"
    output_as: ip_data
  depends_on:
    - start_security

- id: verify_ip
  action: LOGIC__if_else
  params:
    condition: "{{ ip_data is defined and ip_data.ip != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Verification complete. IP: {{ ip_data.ip }}"
    false_branch:
      action: LOGIC__abort
      params:
        reason: "No internet connection on startup."
  depends_on:
    - check_connection
```

---

### 🔄 FLOWS Category
Nodes dedicated to managing and orchestrating other flows.

#### 18. `FLOWS__run_flow` — Run External Flow
Allows you to call and execute another saved flow within Hecos, making it possible to structure automations modularly (as sub-routines or libraries).

| Parameter | Type | Description |
|-----------|------|-------------|
| `flow_id` | string | The ID of the external flow to execute (e.g., the slug/filename, `morning_routine`) |
| `wait` | boolean | If `true` (default), waits for the sub-flow to complete before proceeding. If `false`, starts it in the background in parallel. |
| `pass_context` | boolean | If `true` (default), passes all current variables of the caller flow to the sub-flow. |

**Example 1: Synchronous Modular Execution (Wait)**
The main flow runs the total lights off sub-flow, waits for it to complete, and then announces goodnight.
```yaml
- id: start_1
  action: CONTROL__start

- id: turn_off_house
  action: FLOWS__run_flow
  params:
    flow_id: "total_lights_off"
    wait: true
    pass_context: false
  depends_on:
    - start_1

- id: final_greeting
  action: AUDIO__speak
  params:
    text: "All lights have been turned off. Goodnight!"
  depends_on:
    - turn_off_house
```

**Example 2: Asynchronous Execution (Background - Fire and Forget)**
The flow triggers a heavy data synchronization in the background without blocking user interaction or the rest of the current flow.
```yaml
- id: start_1
  action: CONTROL__start

- id: trigger_backup
  action: FLOWS__run_flow
  params:
    flow_id: "daily_nas_backup"
    wait: false
    pass_context: true
  depends_on:
    - start_1

- id: immediate_notification
  action: SYSTEM__chat_message
  params:
    text: "Backup has been started in the background. You can continue using Hecos freely."
  depends_on:
    - start_1
```

**Example 3: Dynamic Parameter Passing**
Sets variables in the calling flow and passes them to the child flow to customize its output.
```yaml
- id: start_1
  action: CONTROL__start

- id: set_data
  action: LOGIC__set_variable
  params:
    name: notification_recipient
    value: "Tony"
  depends_on:
    - start_1

- id: send_custom_notification
  action: FLOWS__run_flow
  params:
    flow_id: "send_telegram_notification"
    wait: true
    pass_context: true
  depends_on:
    - set_data
```

---

### 👤 USER Category
Nodes dedicated to direct interactive user interactions.

#### 19. `USER__ask_input` — Ask User Input
Pauses flow execution and waits for the user to provide input via chat (text) or voice. The received response is stored in the variable defined in the node's *Output As* field (e.g., `user_input`) to be used by subsequent blocks.

If the flow is interrupted or cancelled (via the "Stop" button), the node detects the cancellation, unblocks the wait, and terminates cleanly.

| Parameter | Type | Description |
|-----------|------|-------------|
| `prompt` | string | The question/prompt to send to the chat and optionally read aloud. |
| `speak` | boolean | If `true` (default), reads the prompt aloud via Text-to-Speech (TTS). |
| `intercept_mode` | choice (`auto`\|`explicit`\|`api_only`) | **auto**: any message in chat is captured as the response.<br>**explicit**: responds only if the message starts with `@flow` (e.g., `@flow 22`). Recommended if using multiple chat clients.<br>**api_only**: only responds via a POST API call to `/api/flows/<run_id>/input`. |
| `multi_run_priority`| choice (`first`\|`all`) | If multiple flows are waiting for input:<br>**first**: assigns the response only to the oldest flow.<br>**all**: sends the same response to all waiting flows. |
| `timeout_seconds` | integer | Maximum wait time in seconds before timing out (default: `0` = wait forever). |
| `on_timeout_continue`| boolean | If `true` (default: `false`), continues execution with an empty string (`""`) on timeout instead of failing the flow. |

**Example 1: Interactive Choice (Yes/No)**
Asks the user if they want to hear a joke, intercepts any response in chat, and branches execution.
```yaml
- id: start_1
  action: CONTROL__start

- id: ask_choice
  action: USER__ask_input
  params:
    prompt: "Would you like to hear a joke?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 60
  output_as: joke_response
  depends_on:
    - start_1

- id: evaluate_response
  action: LOGIC__if_else
  params:
    condition: "'yes' in {{ joke_response | lower }} or 'ok' in {{ joke_response | lower }}"
    true_branch:
      action: AUDIO__speak
      params:
        text: "Why don't scientists trust atoms? Because they make up everything!"
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "No problem, maybe next time."
  depends_on:
    - ask_choice
```

**Example 2: Safe Numeric Setpoint with Timeout**
Asks to enter a target temperature explicitly (using `@flow <temperature>`). If the user does not respond within 15 seconds, it continues using the default value.
```yaml
- id: start_1
  action: CONTROL__start

- id: ask_temperature
  action: USER__ask_input
  params:
    prompt: "At what temperature would you like to set the thermostat? Answer writing '@flow <degrees>'"
    speak: false
    intercept_mode: "explicit"
    timeout_seconds: 15
    on_timeout_continue: true
  output_as: chosen_degrees
  depends_on:
    - start_1

- id: verify_and_set
  action: LOGIC__if_else
  params:
    condition: "{{ chosen_degrees != '' }}"
    true_branch:
      action: SYSTEM__chat_message
      params:
        text: "Setting the temperature to {{ chosen_degrees }} degrees."
    false_branch:
      action: SYSTEM__chat_message
      params:
        text: "No response. Keeping default temperature at 20 degrees."
  depends_on:
    - ask_temperature
```

**Example 3: Sentiment Analysis of Input**
Asks the user how they feel, passes the input to the AI to analyze their mood, and responds accordingly.
```yaml
- id: start_1
  action: CONTROL__start

- id: ask_mood
  action: USER__ask_input
  params:
    prompt: "Hi! How is your day going today?"
    speak: true
    intercept_mode: "auto"
    timeout_seconds: 0
  output_as: user_mood
  depends_on:
    - ask_mood

- id: analyze_sentiment
  action: AI__prompt
  params:
    prompt: "The user replied: '{{ user_mood }}'. Analyze their mood (positive/negative/neutral) and reply with a single sentence of support or happiness suitable for their mood."
    save_to_chat: true
  depends_on:
    - ask_mood
```

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

---

## 7. The Executor and System Commands (Shell and Python)

Among the most powerful nodes in Hecos are those related to the **EXECUTOR** module. These nodes allow you to step outside the boundaries of standard automation and issue actual commands to your operating system (Windows or Linux).

### 7.1 Visible vs. Invisible Execution (Background)

When using the command line (Shell) through Hecos, you must decide whether the user should see what is happening or if it should all run silently behind the scenes.

- **`EXECUTOR__execute_background_command`**: This node is designed to execute commands in *silent* (headless) mode. No black window will open on the desktop. The command will run in the shadows, and the output will be saved in a log file. It is perfect for downloading files, starting servers, or performing maintenance operations without disturbing you.
  *Warning*: If you simply type `cmd` or `bash` in here, the node will create an invisible terminal that will wait infinitely for your input, blocking the flow!
- **`EXECUTOR__execute_shell_command`**: If you wish to **visibly open** a program or a command prompt window on the desktop, you must "detach" the process using your operating system's native command, such as `start` (on Windows) or `gnome-terminal` (on Linux).

> [!TIP]
> **How to execute multiple commands in a row?** You don't need to use one node for each command! You can use the `&&` operator to concatenate them into a single string. Hecos will execute them strictly in sequence. Example: `ipconfig && mkdir new_folder && echo "Done!"`

#### Example 1: Silently Create a Folder (Background)
*Scenario: A flow creates a backup directory without showing anything on screen.*
```yaml
  - id: create_silent_backup
    action: EXECUTOR__execute_background_command
    params:
      command: "mkdir C:\backup_hecos && echo Backup folder created"
```

#### Example 2: Open a Visible Command Prompt (Windows Only)
*Scenario: You want Hecos to open a black CMD window, PING Google, and keep the window open for you to read the result.*
```yaml
  - id: open_visible_cmd
    action: EXECUTOR__execute_shell_command
    params:
      # The /k ("keep") parameter keeps the window open. Use /c ("close") to close it.
      command: "start cmd /k \"ping 8.8.8.8 && echo Ping completed!\""
```

### 7.2 The Cross-Platform Problem (Windows vs. Linux)

If you type `start cmd` in a shell node, you have just made your flow **incompatible with Linux or Mac**. On Linux, `cmd` doesn't exist, and the flow will throw an error. How do you solve this problem if you want to create universal automations?

You have two solutions:
1. **Use native Hecos nodes**: Instead of using `execute_shell_command` and writing `mkdir` or `taskkill`, use the dedicated executor nodes! For example: `EXECUTOR__create_dir`, `EXECUTOR__read_file`, or `EXECUTOR__kill_process`. Hecos will figure out on its own if you are on Windows or Linux and execute the correct command.
2. **Use the ultimate Script Maker: Python!**

### 7.3 `EXECUTOR__run_python_code`: The True Universal Script Maker

Instead of going crazy with commands concatenated by `&&` or `.bat` files, you can use the `EXECUTOR__run_python_code` node. This node provides you with a real editor where you can insert a Python script.

**Why use Python instead of the Shell?**
- **It is Cross-Platform**: The same Python script runs exactly the same on Windows, Linux, and Raspberry Pi.
- **It is Powerful**: You can use complex logic loops, mathematical calculations, or format data much better than in a command prompt.
- **Variables**: You can return the result of your script (via `print`) to save it in an `output_as` variable and pass it to subsequent nodes!

#### Example 3: A Universal Cross-Platform Python Script
*Scenario: A Python script that figures out on its own which operating system it is on, safely creates a folder on the user's desktop, and returns the result to Hecos to speak it aloud.*
```yaml
  - id: universal_python_script
    action: EXECUTOR__run_python_code
    params:
      code: |
        import os
        from pathlib import Path
        
        # Find the Desktop folder on both Windows and Linux
        desktop_dir = Path.home() / "Desktop"
        new_folder = desktop_dir / "Hecos_Magic_Folder"
        
        if not new_folder.exists():
            new_folder.mkdir()
            print("I created the magic folder on the desktop!")
        else:
            print("The folder already existed, no problem.")
    output_as: script_result

  - id: announce_result
    action: AUDIO__speak
    params:
      text: "{{ script_result }}"
    depends_on:
      - universal_python_script
```

This way you have created an automation that you can share with anyone, regardless of the PC or operating system they use!
