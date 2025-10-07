import { test, expect } from '@playwright/test';

test.describe('Config Editor', () => {
  test('loads and displays configuration', async ({ page }) => {
    await page.goto('/');

    // Wait for loading to complete
    await expect(page.getByText('Loading configuration...')).not.toBeVisible({ timeout: 5000 });

    // Check that the page title is present
    await expect(page.getByRole('heading', { name: 'Configuration Editor' })).toBeVisible();

    // Check that buttons are present
    await expect(page.getByRole('button', { name: 'Save' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reload' })).toBeVisible();

    // Check that the textarea is present and has content
    const textarea = page.locator('.config-textarea');
    await expect(textarea).toBeVisible();

    const content = await textarea.inputValue();
    expect(content.length).toBeGreaterThan(0);

    // Verify it's valid JSON
    expect(() => JSON.parse(content)).not.toThrow();

    // Verify it has expected config structure
    const config = JSON.parse(content);
    expect(config).toHaveProperty('profiles');
    expect(config).toHaveProperty('schedules');
  });

  test('validates JSON before saving', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Loading configuration...')).not.toBeVisible({ timeout: 5000 });

    const textarea = page.locator('.config-textarea');

    // Clear and enter invalid JSON
    await textarea.fill('{ invalid json }');

    // Save button should be disabled due to validation error
    const saveButton = page.getByRole('button', { name: 'Save' });
    await expect(saveButton).toBeDisabled();

    // Should show validation error
    await expect(page.getByText(/JSON Error:/)).toBeVisible();
  });

  test('enables save button with valid JSON', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Loading configuration...')).not.toBeVisible({ timeout: 5000 });

    const textarea = page.locator('.config-textarea');
    const saveButton = page.getByRole('button', { name: 'Save' });

    // Get original config
    const originalConfig = await textarea.inputValue();
    const config = JSON.parse(originalConfig);

    // Make a small valid change
    config.test_field = 'test_value';
    await textarea.fill(JSON.stringify(config, null, 2));

    // Save button should be enabled
    await expect(saveButton).toBeEnabled();

    // Restore original config
    await textarea.fill(originalConfig);
  });

  test('shows confirmation dialog before reload', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Loading configuration...')).not.toBeVisible({ timeout: 5000 });

    // Set up dialog handler to dismiss it
    page.on('dialog', dialog => {
      expect(dialog.message()).toContain('Reload configuration now?');
      dialog.dismiss();
    });

    const reloadButton = page.getByRole('button', { name: 'Reload' });
    await reloadButton.click();

    // Button should return to normal state after dialog dismissal
    await expect(reloadButton).toHaveText('Reload');
  });

  test('displays warning banner about authentication', async ({ page }) => {
    await page.goto('/');

    const warningBanner = page.locator('.warning-banner');
    await expect(warningBanner).toBeVisible();
    await expect(warningBanner).toContainText('Development Mode');
    await expect(warningBanner).toContainText('authentication');
  });

  test('clears validation error when user types', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Loading configuration...')).not.toBeVisible({ timeout: 5000 });

    const textarea = page.locator('.config-textarea');

    // Enter invalid JSON to trigger validation error
    await textarea.fill('{ invalid }');
    await expect(page.getByText(/JSON Error:/)).toBeVisible();

    // Start typing - validation error should clear
    await textarea.fill('{ "valid": "json" }');
    await expect(page.getByText(/JSON Error:/)).not.toBeVisible();
  });
});
