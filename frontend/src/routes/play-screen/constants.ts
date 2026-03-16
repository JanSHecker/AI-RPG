export const playScreenClassNames = {
  alert: '!rounded-none !border-accent/35 !bg-black/80',
  field: '!rounded-none !border-accent/30 !bg-black/80 !text-foreground placeholder:!text-muted/50',
  primaryButton:
    '!rounded-none !border-accent/45 !bg-accent/10 !text-accent shadow-none hover:!border-accent hover:!bg-accent/15 hover:!text-accent',
  secondaryButton:
    '!rounded-none !border-accent/30 !bg-transparent !text-foreground shadow-none hover:!border-accent hover:!bg-accent/10 hover:!text-accent',
  dangerButton:
    '!rounded-none !border-danger/50 !bg-danger/10 !text-danger shadow-none hover:!border-danger hover:!bg-danger/15 hover:!text-danger',
  tabList: '!grid-cols-4 !rounded-none !border-accent/20 !bg-black/80 !p-0 !gap-0',
  tabTrigger:
    '!rounded-none !border-x-0 !border-y-0 !border-transparent !px-3 !py-3 !text-[10px] !tracking-[0.3em] data-[state=active]:!border-accent/40 data-[state=active]:!bg-accent/10 data-[state=active]:!text-accent',
  tabContent:
    '!mt-0 !flex-1 !min-h-0 !rounded-none !overflow-hidden !border-x-0 !border-b-0 !border-t !border-accent/20 !bg-black/80 !p-0',
} as const
