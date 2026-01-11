import * as Haptics from 'expo-haptics';

/**
 * Simple sound utility - plays a note when quantity changes
 * On iOS, notification feedback types play system sounds
 */

/**
 * Play increase sound (higher pitch note)
 * Uses Success notification which plays a pleasant "ding" sound on iOS
 */
export async function playIncreaseSound() {
  try {
    // Success notification - plays a pleasant "ding" sound on iOS
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    console.log('🔊 Played increase sound (Success notification)');
  } catch (error) {
    console.error('Error playing increase sound:', error);
    // Fallback to impact
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    } catch (e) {
      // Ignore
    }
  }
}

/**
 * Play decrease sound (lower pitch note)
 * Uses Warning notification which plays a different sound on iOS
 */
export async function playDecreaseSound() {
  try {
    // Warning notification - plays a different sound on iOS
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    console.log('🔊 Played decrease sound (Warning notification)');
  } catch (error) {
    console.error('Error playing decrease sound:', error);
    // Fallback to impact
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch (e) {
      // Ignore
    }
  }
}

/**
 * Initialize sounds (no-op, but kept for compatibility)
 */
export async function initializeSounds() {
  // Haptics don't need initialization
}

/**
 * Cleanup (no-op, but kept for compatibility)
 */
export async function cleanupSounds() {
  // Nothing to cleanup
}

