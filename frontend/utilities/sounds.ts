import { Audio } from 'expo-av';
import * as Haptics from 'expo-haptics';

/**
 * Sound utility for playing beep sounds
 * Uses Audio API with programmatically generated tones
 */

let increaseSound: Audio.Sound | null = null;
let decreaseSound: Audio.Sound | null = null;
let soundsInitialized = false;

/**
 * Generate a simple beep tone as a data URI
 * Uses a simpler approach that works better in React Native
 */
function generateTone(frequency: number, duration: number): string {
  try {
    const sampleRate = 44100;
    const numSamples = Math.floor(sampleRate * duration);
    
    // Create WAV file buffer
    const buffer = new ArrayBuffer(44 + numSamples * 2);
    const view = new DataView(buffer);
    
    // Helper to write strings
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    // WAV header
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + numSamples * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, 1, true); // Mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, numSamples * 2, true);
    
    // Generate sine wave samples
    for (let i = 0; i < numSamples; i++) {
      const t = i / sampleRate;
      // Fade in/out to avoid clicks
      const fadeIn = Math.min(1, t * 50);
      const fadeOut = Math.min(1, (duration - t) * 50);
      const fade = Math.min(fadeIn, fadeOut);
      const sample = Math.sin(2 * Math.PI * frequency * t) * fade * 0.5;
      const intSample = Math.max(-32768, Math.min(32767, Math.floor(sample * 32767)));
      view.setInt16(44 + i * 2, intSample, true);
    }
    
    // Convert to base64 (React Native compatible)
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    // btoa should be available in React Native
    const base64 = btoa(binary);
    return `data:audio/wav;base64,${base64}`;
  } catch (error) {
    console.error('Error generating tone:', error);
    return '';
  }
}

/**
 * Initialize sound effects
 */
export async function initializeSounds() {
  if (soundsInitialized) return;
  
  try {
    console.log('Initializing sounds...');
    await Audio.setAudioModeAsync({
      playsInSilentModeIOS: true,
      allowsRecordingIOS: false,
      staysActiveInBackground: false,
    });

    // Create increase sound (higher pitch ding - 800Hz)
    increaseSound = new Audio.Sound();
    const increaseBeep = generateTone(800, 0.2);
    if (increaseBeep) {
      await increaseSound.loadAsync({ uri: increaseBeep });
      console.log('Increase sound loaded');
    }

    // Create decrease sound (lower pitch - 400Hz)
    decreaseSound = new Audio.Sound();
    const decreaseBeep = generateTone(400, 0.2);
    if (decreaseBeep) {
      await decreaseSound.loadAsync({ uri: decreaseBeep });
      console.log('Decrease sound loaded');
    }
    
    soundsInitialized = true;
    console.log('Sounds initialized successfully');
  } catch (error) {
    console.error('Error initializing sounds:', error);
    soundsInitialized = false;
  }
}

/**
 * Play increase sound (ding)
 */
export async function playIncreaseSound() {
  try {
    // Always provide haptic feedback
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    
    // Try to play sound
    if (increaseSound) {
      const status = await increaseSound.getStatusAsync();
      if (status.isLoaded) {
        await increaseSound.setPositionAsync(0);
        await increaseSound.playAsync();
      } else {
        console.log('Increase sound not loaded, reinitializing...');
        await initializeSounds();
        if (increaseSound) {
          await increaseSound.playAsync();
        }
      }
    } else {
      // Initialize if not done yet
      await initializeSounds();
      if (increaseSound) {
        await increaseSound.playAsync();
      }
    }
  } catch (error) {
    console.error('Error playing increase sound:', error);
  }
}

/**
 * Play decrease sound (lower pitch)
 */
export async function playDecreaseSound() {
  try {
    // Always provide haptic feedback
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    
    // Try to play sound
    if (decreaseSound) {
      const status = await decreaseSound.getStatusAsync();
      if (status.isLoaded) {
        await decreaseSound.setPositionAsync(0);
        await decreaseSound.playAsync();
      } else {
        console.log('Decrease sound not loaded, reinitializing...');
        await initializeSounds();
        if (decreaseSound) {
          await decreaseSound.playAsync();
        }
      }
    } else {
      // Initialize if not done yet
      await initializeSounds();
      if (decreaseSound) {
        await decreaseSound.playAsync();
      }
    }
  } catch (error) {
    console.error('Error playing decrease sound:', error);
  }
}

/**
 * Cleanup sounds
 */
export async function cleanupSounds() {
  try {
    if (increaseSound) {
      await increaseSound.unloadAsync();
      increaseSound = null;
    }
    if (decreaseSound) {
      await decreaseSound.unloadAsync();
      decreaseSound = null;
    }
  } catch (error) {
    // Silently ignore errors
  }
}

