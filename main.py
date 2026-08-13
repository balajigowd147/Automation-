from playwright_classroom import open_classroom


playwright, context, page = open_classroom()

print("\nBrowser is running.")
print("Current URL:", page.url)

input("\nComplete Google login manually if required.")
input("\nAfter you reach Google Classroom, press Enter here...")

print("\nFinal URL:", page.url)

input("\nPress Enter to close the browser...")

context.close()
playwright.stop()