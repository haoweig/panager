import './globals.css'

export const metadata = {
  title: 'Password Manager',
  description: 'Secure Password Manager',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}