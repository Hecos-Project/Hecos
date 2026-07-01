# 🔑 23. Key Manager & Failover

Manage your API keys without system restarts.
- **Auto-Failover**: Instantly switches to the next available key on 429 (Rate Limit) or credential errors.
- **Cooldown**: Temporarily pauses keys during API congestion.
- **Key Pool GUI**: Add and monitor keys via the WebUI Key Manager tab.

### ⚙️ Advanced Settings and Failover Behavior

The Key Manager features an **Advanced Settings** section to let you optimize how Hecos handles API requests and key failover.

Here is a detailed explanation of the parameters:

1. **⏱️ Cloud request timeout (seconds)**
   * **What it does**: Sets the maximum time Hecos will wait for a response from the cloud provider before giving up on the current key.
   * **Why modify it**: If the API is overloaded and unresponsive, a high timeout blocks Hecos in a "thinking" state for too long. A lower value (e.g., 20-30s) allows Hecos to quickly detect the issue and switch to a backup key.
   * **Recommended**: 30 seconds.

2. **🔄 Errored key cooldown (seconds)**
   * **What it does**: When a key receives a rate limit error (HTTP 429) or times out, Hecos puts it "on pause" (cooldown) for the specified time, avoiding wasted attempts.
   * **Why modify it**: If you use free APIs that block for a minute after 10 messages, 60s is ideal. If you have few keys, you might want to reduce this to retry earlier with the same keys.
   * **Recommended**: 60 seconds.

3. **🔁 Max failover retries**
   * **What it does**: Determines the maximum number of *different keys* Hecos will try to contact in sequence for a single user message before returning an error message.
   * **Why modify it**: To avoid infinite loops or overly long requests. Set it to a number equal to the amount of backup keys you have for that provider.
   * **Recommended**: 5.

#### 💡 How failover works:
1. Hecos tries **key #1** with the configured timeout.
2. If the API responds with an error (429 rate limit or 401 unauthorized) or the **timeout** triggers, Hecos marks that key as in "cooldown".
3. Hecos automatically switches to **key #2** and tries again.
4. This repeats until a key works, or until the "Max failover retries" limit is reached.
5. Keys in cooldown automatically become active again once the configured time has elapsed.
