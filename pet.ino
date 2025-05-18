//Arduino Pet-Like Robot - Autonomous Pet Behaviors
// Features:
// - Two servo motors for neck movement (horizontal 360° and vertical 180°)
// - Advanced pet-like autonomous movements and behaviors
// - Personality traits and mood system
// - No IR sensors - purely autonomous behavior

//include the library code:
#include <Servo.h>             
#include <AFMotor.h>           

// Create motor objects
AF_DCMotor Motor1(1, MOTOR12_1KHZ);
AF_DCMotor Motor2(2, MOTOR12_1KHZ);
AF_DCMotor Motor3(3, MOTOR34_1KHZ);
AF_DCMotor Motor4(4, MOTOR34_1KHZ);

// Create servo objects for neck movement
Servo neckHorizontal;  // Horizontal servo for 360° rotation
Servo neckVertical;    // Vertical servo for 180° movement

// Variables for servo positions
int horizontalPos = 90;
int verticalPos = 90;

// Variables for autonomous behavior
unsigned long lastMovementTime = 0;
unsigned long lastLookTime = 0;
unsigned long lastMoodChange = 0;
unsigned long lastSoundTime = 0;

// Personality and mood system
enum Mood {PLAYFUL, SLEEPY, CURIOUS, ALERT, CONTENT};
Mood currentMood = CONTENT;
int energyLevel = 100;       // 0-100 scale
int curiosityLevel = 50;     // 0-100 scale
int playfulnessLevel = 70;   // 0-100 scale

// Behavior variables
int currentBehavior = 0;
int behaviorDuration = 0;
bool isAwake = true;
bool isResting = false;

// Minimum motor speed - increased to ensure motors start
const int MIN_MOTOR_SPEED = 200;

// Sound pin
const int buzzerPin = A0;

void setup() {
  Serial.begin(9600); // Initialize serial communication at 9600 bits per second
  
  // Attach servos to pins
  neckHorizontal.attach(9);  // Horizontal neck servo on pin 9
  neckVertical.attach(10);   // Vertical neck servo on pin 10
  
  // Set servo initial positions (center)
  neckHorizontal.write(90);
  neckVertical.write(90);
  
  // Initialize motors explicitly
  Motor1.run(RELEASE);
  Motor2.run(RELEASE);
  Motor3.run(RELEASE);
  Motor4.run(RELEASE);
  
  // Setup buzzer
  pinMode(buzzerPin, OUTPUT);
  
  // Test all motors briefly to ensure they're working
  testMotors();
  
  // Initial pet-like greeting movement sequence
  petGreeting();
  
  // Initialize random seed for more unpredictable pet behavior
  randomSeed(analogRead(A5));
}

// New function to test motors at startup
void testMotors() {
  Serial.println("Testing motors...");
  
  // Test Motor 1
  Serial.println("Testing Motor 1");
  Motor1.setSpeed(200);
  Motor1.run(FORWARD);
  delay(500);
  Motor1.run(RELEASE);
  
  // Test Motor 2
  Serial.println("Testing Motor 2");
  Motor2.setSpeed(200);
  Motor2.run(FORWARD);
  delay(500);
  Motor2.run(RELEASE);
  
  // Test Motor 3
  Serial.println("Testing Motor 3");
  Motor3.setSpeed(200);
  Motor3.run(FORWARD);
  delay(500);
  Motor3.run(RELEASE);
  
  // Test Motor 4
  Serial.println("Testing Motor 4");
  Motor4.setSpeed(200);
  Motor4.run(FORWARD);
  delay(500);
  Motor4.run(RELEASE);
  
  Serial.println("Motor test complete");
}

void loop() {
  // Update pet state
  updateMoodAndEnergy();
  
  // Execute pet behaviors based on current mood
  executePetBehaviors();
}

// Function to update mood and energy over time
void updateMoodAndEnergy() {
  unsigned long currentTime = millis();
  
  // Update energy level - decreases slowly over time
  if (currentTime - lastMoodChange > 30000) { // Every 30 seconds
    lastMoodChange = currentTime;
    
    // Decrease energy if awake
    if (isAwake) {
      energyLevel -= random(1, 5);
      if (energyLevel < 0) energyLevel = 0;
      
      // Increase or decrease curiosity and playfulness randomly
      curiosityLevel += random(-10, 11);
      playfulnessLevel += random(-10, 11);
      
      // Keep values in range
      curiosityLevel = constrain(curiosityLevel, 0, 100);
      playfulnessLevel = constrain(playfulnessLevel, 0, 100);
      
      // Update mood based on energy and personality traits
      updateMood();
    } else {
      // Increase energy while sleeping
      energyLevel += random(5, 10);
      if (energyLevel > 100) {
        energyLevel = 100;
        isAwake = true; // Wake up when fully rested
        wakeUpBehavior();
      }
    }
    
    Serial.print("Energy: ");
    Serial.print(energyLevel);
    Serial.print(", Mood: ");
    Serial.println(getMoodString());
  }
}

// Function to update pet's mood based on internal state
void updateMood() {
  // Determine mood based on energy and personality traits
  if (energyLevel < 20) {
    currentMood = SLEEPY;
    if (energyLevel < 10 && !isResting) {
      fallAsleep();
    }
  } else if (curiosityLevel > 70) {
    currentMood = CURIOUS;
  } else if (playfulnessLevel > 70 && energyLevel > 50) {
    currentMood = PLAYFUL;
  } else if (energyLevel > 80) {
    currentMood = ALERT;
  } else {
    currentMood = CONTENT;
  }
}

// Convert mood enum to string for debugging
String getMoodString() {
  switch (currentMood) {
    case PLAYFUL: return "Playful";
    case SLEEPY: return "Sleepy";
    case CURIOUS: return "Curious";
    case ALERT: return "Alert";
    case CONTENT: return "Content";
    default: return "Unknown";
  }
}

// Function for executing pet behaviors based on current mood
void executePetBehaviors() {
  unsigned long currentTime = millis();
  
  // Skip behavior execution if sleeping
  if (!isAwake) {
    // Occasional small movements while sleeping
    if (currentTime - lastMovementTime > 10000) { // Every 10 seconds
      lastMovementTime = currentTime;
      if (random(100) < 30) { // 30% chance for sleep movement
        gentleSleepMovement();
      }
    }
    return;
  }
  
  // Change behavior periodically
  if (currentTime - lastMovementTime > behaviorDuration) {
    lastMovementTime = currentTime;
    
    // Select behavior based on current mood
    switch (currentMood) {
      case PLAYFUL:
        playfulBehavior();
        break;
      case SLEEPY:
        sleepyBehavior();
        break;
      case CURIOUS:
        curiousBehavior();
        break;
      case ALERT:
        alertBehavior();
        break;
      case CONTENT:
        contentBehavior();
        break;
    }
  }
  
  // Periodic head/neck movement to look around
  if (currentTime - lastLookTime > 2000) { // Look around every 2 seconds
    lastLookTime = currentTime;
    
    // Behavior depends on mood
    if (currentMood == ALERT) {
      quickLookAround();
    } else if (currentMood == CURIOUS) {
      intenselyExamineSomething();
    } else if (currentMood != SLEEPY) {
      casualLookAround();
    }
  }
  
  // Occasional sounds based on mood
  if (currentTime - lastSoundTime > 8000) { // Every 8 seconds
    lastSoundTime = currentTime;
    if (random(100) < 30) { // 30% chance to make sound
      makeMoodSound();
    }
  }
}

// Mood-specific behaviors

void playfulBehavior() {
  int behavior = random(5);
  switch (behavior) {
    case 0: // Spin around playfully
      spinAround();
      behaviorDuration = random(1000, 3000);
      break;
    case 1: // Zigzag movement
      zigzagMovement();
      behaviorDuration = random(3000, 6000);
      break;
    case 2: // Playful pounce
      playfulPounce();
      behaviorDuration = random(2000, 4000);
      break;
    case 3: // Circle dance
      circleDance();
      behaviorDuration = random(4000, 7000);
      break;
    case 4: // Playbow
      playBow();
      behaviorDuration = random(2000, 3000);
      break;
  }
  energyLevel -= random(2, 5); // Playing uses energy
}

void sleepyBehavior() {
  int behavior = random(3);
  switch (behavior) {
    case 0: // Slow movement
      moveForward(MIN_MOTOR_SPEED - 50);
      delay(random(500, 1500));
      stopMoving();
      behaviorDuration = random(4000, 8000);
      break;
    case 1: // Find spot to rest
      turnSlowly();
      moveForward(MIN_MOTOR_SPEED - 50);
      delay(random(1000, 2000));
      stopMoving();
      neckVertical.write(120); // Head down
      behaviorDuration = random(5000, 10000);
      break;
    case 2: // Fall asleep if very tired
      if (energyLevel < 15) {
        fallAsleep();
      } else {
        slowStretch();
        behaviorDuration = random(3000, 6000);
      }
      break;
  }
}

void curiousBehavior() {
  int behavior = random(4);
  switch (behavior) {
    case 0: // Move to investigate
      moveForward(MIN_MOTOR_SPEED);
      delay(random(1000, 3000));
      stopMoving();
      intenselyExamineSomething();
      behaviorDuration = random(3000, 7000);
      break;
    case 1: // Look around carefully
      for (int i = 0; i < 3; i++) {
        int side = random(2);
        if (side == 0) {
          moveLeft(MIN_MOTOR_SPEED);
        } else {
          moveRight(MIN_MOTOR_SPEED);
        }
        delay(random(300, 800));
        stopMoving();
        intenselyExamineSomething();
        delay(800);
      }
      behaviorDuration = random(4000, 8000);
      break;
    case 2: // Circle around object of interest
      slowCircle();
      behaviorDuration = random(5000, 9000);
      break;
    case 3: // Approach and examine
      moveForward(MIN_MOTOR_SPEED);
      delay(random(700, 1500));
      stopMoving();
      neckVertical.write(60); // Look down
      delay(1000);
      neckVertical.write(90);
      behaviorDuration = random(3000, 6000);
      break;
  }
  energyLevel -= random(1, 3); // Curiosity uses some energy
}

void alertBehavior() {
  int behavior = random(3);
  switch (behavior) {
    case 0: // Quick turn and scan
      moveRight(MIN_MOTOR_SPEED + 20);
      delay(random(300, 600));
      stopMoving();
      quickLookAround();
      behaviorDuration = random(2000, 4000);
      break;
    case 1: // Back up and look
      moveBackward(MIN_MOTOR_SPEED);
      delay(random(500, 1000));
      stopMoving();
      for (int i = 0; i < 3; i++) {
        neckHorizontal.write(random(30, 150));
        delay(300);
      }
      behaviorDuration = random(3000, 5000);
      break;
    case 2: // Alert stance
      stopMoving();
      neckVertical.write(70); // Head up slightly
      for (int i = 0; i < 5; i++) {
        neckHorizontal.write(random(60, 120));
        delay(200);
      }
      makeSound(1000, 50); // Alert sound
      behaviorDuration = random(3000, 6000);
      break;
  }
  energyLevel -= random(2, 4); // Being alert uses energy
}

void contentBehavior() {
  int behavior = random(4);
  switch (behavior) {
    case 0: // Leisurely stroll
      moveForward(MIN_MOTOR_SPEED - 30);
      behaviorDuration = random(3000, 7000);
      break;
    case 1: // Gentle turn and pause
      turnSlowly();
      delay(random(1000, 2000));
      stopMoving();
      behaviorDuration = random(4000, 8000);
      break;
    case 2: // Rest in place
      stopMoving();
      neckVertical.write(100); // Slightly relaxed head position
      behaviorDuration = random(5000, 10000);
      break;
    case 3: // Gentle stretch
      slowStretch();
      behaviorDuration = random(4000, 7000);
      break;
  }
  energyLevel -= random(1, 2); // Content behavior uses little energy
}

// Specialized pet movement functions

void zigzagMovement() {
  for (int i = 0; i < random(2, 5); i++) {
    moveLeft(MIN_MOTOR_SPEED);
    delay(random(300, 700));
    moveForward(MIN_MOTOR_SPEED);
    delay(random(400, 800));
    moveRight(MIN_MOTOR_SPEED);
    delay(random(300, 700));
    moveForward(MIN_MOTOR_SPEED);
    delay(random(400, 800));
  }
  stopMoving();
}

void playfulPounce() {
  // Wind up for pounce
  moveBackward(MIN_MOTOR_SPEED);
  delay(random(500, 800));
  stopMoving();
  neckVertical.write(70); // Head up
  delay(500);
  
  // Pounce forward quickly
  moveForward(255);
  delay(random(800, 1200));
  stopMoving();
  
  // Playful head movements after pounce
  for (int i = 0; i < 3; i++) {
    neckHorizontal.write(random(60, 120));
    neckVertical.write(random(80, 100));
    delay(200);
  }
}

void circleDance() {
  int direction = random(2);
  int circleSpeed = MIN_MOTOR_SPEED + 20;
  
  for (int i = 0; i < random(1, 4); i++) {
    if (direction == 0) {
      // Circle left
      Motor1.setSpeed(circleSpeed);
      Motor1.run(FORWARD);
      Motor2.setSpeed(circleSpeed/2);
      Motor2.run(FORWARD);
      Motor3.setSpeed(circleSpeed/2);
      Motor3.run(FORWARD);
      Motor4.setSpeed(circleSpeed);
      Motor4.run(FORWARD);
    } else {
      // Circle right
      Motor1.setSpeed(circleSpeed/2);
      Motor1.run(FORWARD);
      Motor2.setSpeed(circleSpeed);
      Motor2.run(FORWARD);
      Motor3.setSpeed(circleSpeed);
      Motor3.run(FORWARD);
      Motor4.setSpeed(circleSpeed/2);
      Motor4.run(FORWARD);
    }
    delay(random(1500, 3000));
  }
  stopMoving();
}

void playBow() {
  // Play bow - front down, rear up like dogs do
  stopMoving();
  neckVertical.write(130); // Head way down
  delay(800);
  
  // Small bounce backward
  moveBackward(MIN_MOTOR_SPEED);
  delay(300);
  stopMoving();
  
  // Return to normal
  neckVertical.write(90);
  delay(500);
  
  // Maybe a small spin after the bow
  if (random(100) > 50) {
    spinAround();
  }
}

void slowStretch() {
  // Stretch like a cat
  stopMoving();
  
  // Stretch head forward and down
  neckVertical.write(120);
  delay(800);
  
  // Extend stretch
  moveForward(MIN_MOTOR_SPEED - 50);
  delay(700);
  stopMoving();
  
  // Stretch head up
  for (int pos = 120; pos >= 70; pos--) {
    neckVertical.write(pos);
    delay(30);
  }
  delay(800);
  
  // Return to normal
  neckVertical.write(90);
}

void turnSlowly() {
  int direction = random(2);
  int turnSpeed = MIN_MOTOR_SPEED - 50;
  
  if (direction == 0) {
    moveLeft(turnSpeed);
  } else {
    moveRight(turnSpeed);
  }
  delay(random(800, 1500));
  stopMoving();
}

void slowCircle() {
  // Move in a slow circle as if examining something
  int direction = random(2);
  int circleSpeed = MIN_MOTOR_SPEED - 30;
  
  if (direction == 0) {
    // Circle left slowly
    Motor1.setSpeed(circleSpeed);
    Motor1.run(FORWARD);
    Motor2.setSpeed(circleSpeed/3);
    Motor2.run(FORWARD);
    Motor3.setSpeed(circleSpeed/3);
    Motor3.run(FORWARD);
    Motor4.setSpeed(circleSpeed);
    Motor4.run(FORWARD);
  } else {
    // Circle right slowly
    Motor1.setSpeed(circleSpeed/3);
    Motor1.run(FORWARD);
    Motor2.setSpeed(circleSpeed);
    Motor2.run(FORWARD);
    Motor3.setSpeed(circleSpeed);
    Motor3.run(FORWARD);
    Motor4.setSpeed(circleSpeed/3);
    Motor4.run(FORWARD);
  }
  
  // During circle, look toward center
  if (direction == 0) {
    neckHorizontal.write(135); // Look left into circle
  } else {
    neckHorizontal.write(45);  // Look right into circle
  }
  
  delay(random(3000, 5000));
  stopMoving();
  neckHorizontal.write(90); // Return to center
}

void fallAsleep() {
  // Sleep actions
  Serial.println("Falling asleep");
  stopMoving();
  
  // Head down motion
  for (int pos = verticalPos; pos < 120; pos++) {
    neckVertical.write(pos);
    delay(30);
  }
  
  // Make a sleepy sound
  makeSound(300, 200);
  delay(200);
  makeSound(200, 300);
  
  isAwake = false;
  isResting = true;
}

void wakeUpBehavior() {
  Serial.println("Waking up");
  
  // Slowly raise head
  for (int pos = 120; pos > 90; pos--) {
    neckVertical.write(pos);
    delay(30);
  }
  
  // Wake up wiggle
  gentleWiggle();
  
  // Wake up sound
  makeSound(600, 100);
  delay(100);
  makeSound(800, 100);
  
  isAwake = true;
  isResting = false;
  
  // Reset mood to content after sleep
  currentMood = CONTENT;
}

void gentleSleepMovement() {
  // Small movements while sleeping
  int currentH = neckHorizontal.read();
  int currentV = neckVertical.read();
  
  // Small head adjustment
  neckHorizontal.write(currentH + random(-10, 11));
  
  // Don't lift head too much during sleep
  int newV = currentV + random(-5, 6);
  newV = constrain(newV, 100, 130); // Keep head lowered
  neckVertical.write(newV);
  
  // Occasionally make sleep sound
  if (random(100) < 30) {
    makeSound(200, 300); // Low, quiet sound
  }
}

void gentleWiggle() {
  // Gentle wiggle like when waking up
  for (int i = 0; i < 3; i++) {
    moveLeft(MIN_MOTOR_SPEED - 50);
    delay(200);
    moveRight(MIN_MOTOR_SPEED - 50);
    delay(200);
  }
  stopMoving();
}

// Looking behavior functions

void casualLookAround() {
  // Casual, relaxed looking around
  int newHorizontal = random(50, 130); // Not too extreme
  int newVertical = random(80, 100);   // Mostly level
  
  // Move to new position gradually
  smoothServoMove(neckHorizontal, horizontalPos, newHorizontal, 20);
  smoothServoMove(neckVertical, verticalPos, newVertical, 20);
  
  horizontalPos = newHorizontal;
  verticalPos = newVertical;
}

void quickLookAround() {
  // Quick, alert head movements
  for (int i = 0; i < random(3, 6); i++) {
    neckHorizontal.write(random(30, 150));
    delay(250);
  }
  
  // Return to a watchful forward position
  neckHorizontal.write(90);
  neckVertical.write(80); // Slightly up, alert position
}

void intenselyExamineSomething() {
  // Focused examination of something interesting
  int lookTarget = random(40, 140);
  
  // Move to look at target
  smoothServoMove(neckHorizontal, horizontalPos, lookTarget, 15);
  
  // Series of small adjustments like focusing on something
  for (int i = 0; i < random(3, 6); i++) {
    int microAdjust = random(-10, 11);
    neckHorizontal.write(lookTarget + microAdjust);
    
    // Occasionally look up and down at the object
    neckVertical.write(random(70, 110));
    delay(400);
  }
  
  horizontalPos = lookTarget;
  verticalPos = neckVertical.read();
}

// Utility functions

void smoothServoMove(Servo &servo, int startPos, int endPos, int stepDelay) {
  int step = (endPos > startPos) ? 1 : -1;
  
  for (int pos = startPos; pos != endPos; pos += step) {
    servo.write(pos);
    delay(stepDelay);
  }
  
  servo.write(endPos); // Ensure final position is set
}

void makeSound(int frequency, int duration) {
  tone(buzzerPin, frequency, duration);
}

void makeMoodSound() {
  switch (currentMood) {
    case PLAYFUL:
      // Happy, higher pitched sounds
      tone(buzzerPin, random(800, 1200), random(50, 150));
      delay(100);
      tone(buzzerPin, random(900, 1300), random(50, 150));
      break;
    case SLEEPY:
      // Low, slow sounds
      tone(buzzerPin, random(200, 400), random(200, 500));
      break;
    case CURIOUS:
      // Medium pitched, questioning sounds
      tone(buzzerPin, random(500, 800), random(100, 200));
      delay(100);
      tone(buzzerPin, random(600, 900), random(100, 150));
      break;
    case ALERT:
      // Sharp, quick sounds
      tone(buzzerPin, random(700, 1000), random(50, 100));
      delay(50);
      tone(buzzerPin, random(700, 1000), random(50, 100));
      break;
    case CONTENT:
      // Gentle, medium pitched sounds
      tone(buzzerPin, random(400, 700), random(150, 300));
      break;
  }
}

// Function for initial greeting movement
void petGreeting() {
  // Head movement greeting
  for (int i = 0; i < 2; i++) {
    // Look left
    for (int angle = 90; angle < 150; angle += 3) {
      neckHorizontal.write(angle);
      delay(15);
    }
    // Look right
    for (int angle = 150; angle > 30; angle -= 3) {
      neckHorizontal.write(angle);
      delay(15);
    }
    // Back to center
    for (int angle = 30; angle < 90; angle += 3) {
      neckHorizontal.write(angle);
      delay(15);
    }
  }
  
  // Vertical nod
  for (int i = 0; i < 2; i++) {
    // Look up
    for (int angle = 90; angle < 130; angle += 3) {
      neckVertical.write(angle);
      delay(15);
    }
    // Look down
    for (int angle = 130; angle > 60; angle -= 3) {
      neckVertical.write(angle);
      delay(15);
    }
    // Back to center
    for (int angle = 60; angle < 90; angle += 3) {
      neckVertical.write(angle);
      delay(15);
    }
  }
  
  // Greeting sound
  makeSound(800, 100);
  delay(100);
  makeSound(1000, 100);
  delay(100);
  makeSound(1200, 100);
  
  // Do a little happy dance with the wheels
  spinAround();
}

// Function for playful spinning
void spinAround() {
  // Spin in place with higher speed to ensure motors move
  Motor1.setSpeed(200);
  Motor1.run(FORWARD);
  Motor2.setSpeed(200);
  Motor2.run(BACKWARD);
  Motor3.setSpeed(200);
  Motor3.run(FORWARD);
  Motor4.setSpeed(200);
  Motor4.run(BACKWARD);
  
  // Spin duration
  delay(random(500, 1500));
  
  // Stop after spinning
  stopMoving();
}

// Basic movement functions
void moveForward(int speed) {
  // Ensure speed is sufficient to start motors
  if (speed < MIN_MOTOR_SPEED - 50) speed = MIN_MOTOR_SPEED - 50;
  
  Serial.println("Moving Forward");
  Motor1.setSpeed(speed);
  Motor1.run(FORWARD);
  Motor2.setSpeed(speed);
  Motor2.run(FORWARD);
  Motor3.setSpeed(speed);
  Motor3.run(FORWARD);
  Motor4.setSpeed(speed);
  Motor4.run(FORWARD);
}

void moveBackward(int speed) {
  // Ensure speed is sufficient to start motors
  if (speed < MIN_MOTOR_SPEED - 50) speed = MIN_MOTOR_SPEED - 50;
  
  Serial.println("Moving Backward");
  Motor1.setSpeed(speed);
  Motor1.run(BACKWARD);
  Motor2.setSpeed(speed);
  Motor2.run(BACKWARD);
  Motor3.setSpeed(speed);
  Motor3.run(BACKWARD);
  Motor4.setSpeed(speed);
  Motor4.run(BACKWARD);
}

void moveLeft(int speed) {
  // Ensure speed is sufficient to start motors
  if (speed < MIN_MOTOR_SPEED - 50) speed = MIN_MOTOR_SPEED - 50;
  
  Serial.println("Moving Left");
  Motor1.setSpeed(speed);
  Motor1.run(FORWARD);
  Motor2.setSpeed(speed);
  Motor2.run(BACKWARD);
  Motor3.setSpeed(speed);
  Motor3.run(BACKWARD);
  Motor4.setSpeed(speed);
  Motor4.run(FORWARD);
}

void moveRight(int speed) {
  // Ensure speed is sufficient to start motors
  if (speed < MIN_MOTOR_SPEED - 50) speed = MIN_MOTOR_SPEED - 50;
  
  Serial.println("Moving Right");
  Motor1.setSpeed(speed);
  Motor1.run(BACKWARD);
  Motor2.setSpeed(speed);
  Motor2.run(FORWARD);
  Motor3.setSpeed(speed);
  Motor3.run(FORWARD);
  Motor4.setSpeed(speed);
  Motor4.run(BACKWARD);
}

void stopMoving() {
  Serial.println("Stopping");
  Motor1.setSpeed(0);
  Motor1.run(RELEASE);
  Motor2.setSpeed(0);
  Motor2.run(RELEASE);
  Motor3.setSpeed(0);
  Motor3.run(RELEASE);
  Motor4.setSpeed(0);
  Motor4.run(RELEASE);
}