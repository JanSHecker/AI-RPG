import { expect, test } from '@playwright/test'

test('boot flow, proposal flow, and combat survive reloads', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('button', { name: /new game/i })).toBeVisible()

  await page.getByRole('button', { name: /create save and enter/i }).click()

  await expect(page.getByText('Web Console')).not.toBeVisible({ timeout: 1000 }).catch(() => {})
  await expect(page.getByPlaceholder('Type a freeform action or a slash command...')).toBeVisible()

  const missingApiKeyWarning = page.getByText(/AI_RPG_API_KEY is not configured/i)
  if (await missingApiKeyWarning.isVisible().catch(() => false)) {
    await expect(missingApiKeyWarning).toBeVisible()
    return
  }

  await page.getByPlaceholder('Type a freeform action or a slash command...').fill('talk mayor')
  await page.getByRole('button', { name: /transmit/i }).click()
  await expect(page.getByText(/pending proposal/i)).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('main').getByText('talk mayor')).toHaveCount(0)
  await page.getByRole('button', { name: /^confirm$/i }).click()
  await expect(page.getByRole('main').getByText('talk mayor')).toBeVisible()
  await expect(page.locator('summary', { hasText: 'Proposed action details' }).first()).toBeVisible()

  await page.getByRole('tab', { name: /inventory/i }).click()
  await expect(page.getByText('Inventory: empty')).toBeVisible()
  await page.getByRole('tab', { name: /map/i }).click()
  await expect(page.getByText('Ruined Watchtower', { exact: true })).toBeVisible()

  await page.getByPlaceholder('Type a freeform action or a slash command...').fill('head to watchtower')
  await page.getByRole('button', { name: /transmit/i }).click()
  await expect(page.getByText(/pending proposal/i)).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: /^confirm$/i }).click()

  await page.getByPlaceholder('Type a freeform action or a slash command...').fill('attack goblin')
  await page.getByRole('button', { name: /transmit/i }).click()
  await expect(page.getByText(/pending proposal/i)).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: /^confirm$/i }).click()

  await expect(page.getByText('Combat Monitor')).toBeVisible()
  await expect(page.getByText(/^Round \d+$/i)).toBeVisible()
  await expect(page.getByText(/your turn/i)).toBeVisible()

  await page.reload()
  await expect(page.getByText('Combat Monitor')).toBeVisible()
  await expect(page.getByText(/^Round \d+$/i)).toBeVisible()
  await expect(page.getByText(/Wanderer .* Goblin Scout\./i).first()).toBeVisible()
})
