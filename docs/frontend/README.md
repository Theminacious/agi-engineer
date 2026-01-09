# 🚀 Frontend Setup & Quick Start

## What Changed?
The frontend was upgraded from basic custom components to **shadcn/ui** - a modern, production-ready component system.

---

## ⚡ Quick Setup (5 minutes)

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development
```bash
npm run dev
```

Visit: `http://localhost:3000`

---

## 📦 What You Get

### New Components
- **Button** - Multiple styles (default, outline, destructive, etc.)
- **Card** - For displaying content
- **Alert** - For error/info messages  
- **Badge** - For status labels
- **Table** - For data display
- **Skeleton** - For loading states
- **Header** - Navigation with mobile menu

### New Features
✅ Dark mode support  
✅ Mobile responsive design  
✅ 700+ icons (lucide-react)  
✅ Full TypeScript support  
✅ Better accessibility  

---

## 🎨 Using Components

### Button
```tsx
import { Button } from '@/components/ui'

<Button>Click me</Button>
<Button variant="outline">Outline</Button>
<Button size="sm">Small</Button>
```

### Card
```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui'

<Card>
  <CardHeader>
    <CardTitle>My Title</CardTitle>
  </CardHeader>
  <CardContent>Content here</CardContent>
</Card>
```

### Badge
```tsx
import { Badge } from '@/components/ui'

<Badge>Default</Badge>
<Badge variant="safe">✅ Safe</Badge>
<Badge variant="destructive">❌ Error</Badge>
```

### Icons
```tsx
import { Menu, LogOut, Home } from 'lucide-react'

<Menu className="w-6 h-6" />
```

---

## 📁 Project Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── auth/page.tsx           # ✨ Login page (improved)
│   ├── dashboard/page.tsx      # ✨ Dashboard (improved)
│   └── runs/                   # Analysis runs (TODO)
│
├── components/
│   ├── layout.tsx              # Navigation & layouts
│   └── ui/                     # Component library
│       ├── button.tsx
│       ├── card.tsx
│       ├── alert.tsx
│       ├── badge.tsx
│       ├── skeleton.tsx
│       ├── table.tsx
│       └── index.ts
│
├── lib/
│   ├── api.ts                  # API client
│   └── utils.ts                # Helper functions
│
├── globals.css                 # ✨ Updated with CSS variables
├── tailwind.config.ts          # ✨ Extended for dark mode
└── package.json                # ✨ Updated dependencies
```

---

## 🔧 Common Tasks

### Add a New Component

1. Create file in `/components/ui/my-component.tsx`:
```tsx
import { cn } from '@/lib/utils'

export function MyComponent({ className, ...props }) {
  return <div className={cn('base-styles', className)} {...props} />
}
```

2. Export from `/components/ui/index.ts`:
```tsx
export { MyComponent } from '@/components/ui/my-component'
```

3. Use it:
```tsx
import { MyComponent } from '@/components/ui'
```

### Use Dark Mode
Components automatically work in both light and dark modes. No extra code needed!

### Add Icons
```tsx
import { IconName } from 'lucide-react'
<IconName className="w-6 h-6" />
```

See all icons: https://lucide.dev

---

## ⚠️ If Something Goes Wrong

| Issue | Solution |
|-------|----------|
| Module not found | Run `npm install` |
| Styles not working | Restart dev server: `npm run dev` |
| Type errors | Clear cache: `rm -rf .next` |
| Pages not loading | Check console for errors |

---

## 📚 Key Files to Know

| File | Purpose |
|------|---------|
| `app/layout.tsx` | Root layout with metadata |
| `app/auth/page.tsx` | Login page with OAuth |
| `app/dashboard/page.tsx` | Main dashboard |
| `components/layout.tsx` | Header & common layouts |
| `components/ui/` | All UI components |
| `tailwind.config.ts` | Theme configuration |
| `globals.css` | Global styles & CSS variables |

---

## 🎯 Next Steps

### Immediate
1. ✅ Run `npm install`
2. ✅ Run `npm run dev`
3. ✅ Test pages load

### Soon
- [ ] Create `/runs/[id]` page for run details
- [ ] Add settings page
- [ ] Create form components

### Later
- [ ] Add data tables with sorting
- [ ] Add toast notifications
- [ ] Add advanced filters

---

## 📖 Learn More

- **shadcn/ui components:** https://ui.shadcn.com
- **Tailwind CSS:** https://tailwindcss.com
- **Icons:** https://lucide.dev
- **Next.js:** https://nextjs.org/docs

---

## ✅ Verification Checklist

After setup:
- [ ] `npm install` completes
- [ ] `npm run dev` starts
- [ ] Login page loads at http://localhost:3000/auth
- [ ] Dashboard accessible
- [ ] No console errors
- [ ] Mobile layout looks good

---

**Version:** 2.1.0  
**Last Updated:** Jan 9, 2026  
**Status:** Ready to use ✅
