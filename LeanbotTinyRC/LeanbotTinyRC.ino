#include <Leanbot.h>

#define TINY_RC_VERSION "Leanbot Tiny RC 260918:092800"

void setup() {
  Leanbot.begin();
  LbDelay(100);
  Serial.println(TINY_RC_VERSION);
}

// Chờ có command từ Serial
bool waitSerialCommand(long timeout) {
  long timeout_target = millis() + timeout;

  while ((long)(millis() - timeout_target) < 0) {
    if (Serial.available() > 0)
      return true;
  }
  return false;
}

// Xử lý command r/60/70
void Leanbot_run(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int left = args.substring(0, pos).toInt();
  int right = args.substring(pos + 1).toInt();

  LbMotion.runLR(left, right);
}

// Xử lý command rfb/2000/700
void runFwBw(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int speed = args.substring(0, pos).toInt();
  int durationMs = args.substring(pos + 1).toInt();

  LbMotion.stopAndWait();
  LbMotion.runLR(+speed, +speed);
  LbDelay(durationMs);
  LbMotion.stopAndWait();
  LbMotion.runLR(-speed, -speed);
  LbDelay(durationMs);
  LbMotion.stopAndWait();
}

// Xử lý command spst/2000/700
void spinSteps(String args) {

  int pos = args.indexOf('/');

  if (pos < 0)
    return;

  int speed = args.substring(0, pos).toInt();
  int rotationSteps = args.substring(pos + 1).toInt();

  LbMotion.stopAndWait();
  LbMotion.runLR(+speed, -speed);
  LbMotion.waitRotation(rotationSteps);
  LbMotion.stopAndWait();
}

void stopLeanbot(void) {
  Serial.println("Leanbot Stop");
  LbMotion.runLR(0, 0);
}

void reportCommand(String cmd, String status) {
  Serial.print(cmd);
  Serial.print("/");
  Serial.println(status);
}

void loop() {

  // Chờ command trong tối đa 3000 ms
  while (waitSerialCommand(3000)) {

    String message = Serial.readStringUntil('\n');
    message.trim();

    // -------------------------
    // Parse command
    // r/60/70
    // ^^
    // command = r
    // args    = 60/70
    // -------------------------

    int pos1 = message.indexOf('/');

    if (pos1 < 0)
      continue;

    String cmd = message.substring(0, pos1);
    String args = message.substring(pos1 + 1);

    // -------------------------
    // Execute command
    // -------------------------

    reportCommand(message, "START");

    if (cmd == "r") { // run RL
      Leanbot_run(args);
    } else if (cmd == "rfb") {
      runFwBw(args);
    } else if (cmd == "spst") {
      spinSteps(args);
    }

    reportCommand(message, "END");
  }

  // Không có command mới trong 3 giây
  stopLeanbot();
}