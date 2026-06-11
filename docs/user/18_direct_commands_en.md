# 18. Direct Commands (HDCS)

Imagine having a **magic wand** that lets you give precise orders to Hecos without having to have a long conversation with the Artificial Intelligence. This magic wand is called **HDCS (Hecos Direct Command System)**, or simply: **Direct Commands**.

Normally, when you write to Hecos, the AI has to read your message, think about what you want to do, choose the right tool, and then execute it. Sometimes, however, you know *exactly* what you want to do and you want it to happen **immediately**, in the blink of an eye!

That's what direct commands are for. They all start with a slash **`/`** and tell the system to execute an action right away, completely bypassing the AI's "brain".

---

## 🎩 How to use them in the Chat

Using direct commands in the chat is as easy as using emojis on WhatsApp!

1. Click on the chat bar where you usually type your messages.
2. Type the **`/`** (slash) character.
3. **Magic!** A dropdown menu will appear right above the text box.
4. This menu contains *all* of Hecos's secret powers (over 150 commands!). 
5. You can scroll through the list with your mouse, or you can keep typing to filter the list. For example, if you type `/weather`, you will see the weather command appear.
6. Press **Tab** or click on the command with your mouse to choose it.
7. If the command needs extra information (like the city for the weather), it will leave a space for you. Type, for example, `/weather London` and press **Enter**. Done!

### Practical Examples in Chat:
- **Want the weather in London?** Type `/weather London` and press Enter.
- **Want to generate an image?** Type `/img a space kitten` and press Enter.
- **Want to restart the system?** Type `/reboot_system` and press Enter.

---

## 🔍 The "Spotlight": Commands always at your fingertips

What if you're not in the chat? Maybe you're looking at the plugins page or reading another screen. Don't worry! You can use direct commands *wherever* you are thanks to the **Spotlight**.

The Spotlight is a special floating search bar. To summon it:
1. Press the secret combination on your keyboard: **`Ctrl + Alt + Space`** (press Control, Alt, and the spacebar together).
2. The screen will slightly dim and a beautiful search bar will appear in the center.
3. Type what you're looking for (e.g. `img` or `weather` or `calendar`).
4. Select the command with the arrow keys and press **Enter**. 
5. Hecos will execute the action instantly in the background and show you a little confirmation message!

---

## 🧩 Using Direct Commands in "Flows"

Flows is the place where you create automatic routines by linking many nodes together as if they were Lego bricks. 
Sometimes, you might want to use a direct command inside a Flow, to ensure an action is executed precisely without asking the AI.

To do this, you just need to use a special node:

1. In the left menu of Flows, open the **SYSTEM** or **EXECUTOR** category.
2. Find the brick called **`execute_slash_command`** and drag it onto your screen.
3. This node has a text field called `command`. That's where you need to write the command you want to execute!
4. **The magician's trick:** If you click on the text box of the node and type `/`, the autocomplete dropdown will open just like in the chat! Select the command, and it will be written for you.
5. Alternatively, you can always press `Ctrl + Alt + Space` to search for the command. If you are inside the node's text box, pressing Enter won't execute the command right away, but will magically **paste** it into the node, ready to be saved!

### Practical Example in Flows:
Do you want to create a flow that every morning at 8:00 turns on a device via a Web request, and then generates a good morning photo for you?
1. Place a `TIME__cron_trigger` node set for 8:00.
2. Place an `execute_slash_command` node and in the *command* parameter write: `/browser.open_url https://turn-on-the-light.com`.
3. Connect another `execute_slash_command` node and write: `/img A beautiful rising sun`.
4. Save the flow! 
Now you have created a super-reliable routine because it doesn't depend on the AI's imagination, but executes direct orders exactly.

---

## 💡 Summary: Why use direct commands?

- **They are lightning fast:** They skip the "thinking" brain and go straight to the action.
- **They are precise:** They always and only do exactly what you tell them to do.
- **They help you discover Hecos:** By scrolling through the list by typing `/`, you can discover tons of Hecos's powers that you might not even have known it had!
