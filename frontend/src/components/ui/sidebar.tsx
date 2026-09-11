import React, { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { SidebarContext, useSidebar } from "./sidebar-context";

export interface Links {
  label: string;
  href?: string;
  icon: React.JSX.Element | React.ReactNode;
  badge?: number;
  onClick?: () => void;
  isActive?: boolean;
}

export const SidebarProvider = ({
  children,
  open: openProp,
  setOpen: setOpenProp,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  const [openState, setOpenState] = useState(false);

  const open = openProp !== undefined ? openProp : openState;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setOpenState;

  return (
    <SidebarContext.Provider value={{ open, setOpen, animate }}>
      {children}
    </SidebarContext.Provider>
  );
};

export const Sidebar = ({
  children,
  open,
  setOpen,
  animate = true,
}: {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  animate?: boolean;
}) => {
  return (
    <SidebarProvider open={open} setOpen={setOpen} animate={animate}>
      {children}
    </SidebarProvider>
  );
};

export const SidebarBody = (props: React.ComponentProps<typeof motion.div>) => {
  return (
    <>
      <DesktopSidebar {...props} />
      <MobileSidebar {...(props as React.ComponentProps<"div">)} />
    </>
  );
};

export const DesktopSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<typeof motion.div>) => {
  const { open, setOpen, animate } = useSidebar();
  return (
    <motion.div
      className={cn(
        "h-screen sticky top-0 px-2.5 py-4 hidden md:flex md:flex-col bg-neutral-100 dark:bg-neutral-950 shrink-0 z-30 transition-[width] duration-200 ease-in-out",
        className
      )}
      animate={{
        width: animate ? (open ? "260px" : "60px") : "260px",
      }}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export const MobileSidebar = ({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) => {
  const { open, setOpen } = useSidebar();
  return (
    <div
      className={cn(
        "h-14 px-4 flex flex-row md:hidden items-center justify-between bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 w-full"
      )}
      {...props}
    >
      <div className="flex justify-end z-20 w-full">
        <Menu
          className="text-neutral-800 dark:text-neutral-200 cursor-pointer w-5 h-5"
          onClick={() => setOpen(!open)}
        />
      </div>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ x: "-100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "-100%", opacity: 0 }}
            transition={{
              duration: 0.3,
              ease: "easeInOut",
            }}
            className={cn(
              "fixed h-full w-full inset-0 bg-white dark:bg-neutral-900 p-6 z-[100] flex flex-col justify-between",
              className
            )}
          >
            <div
              className="absolute right-6 top-6 z-50 text-neutral-800 dark:text-neutral-200 cursor-pointer p-1 rounded-md hover:bg-neutral-100 dark:hover:bg-neutral-800"
              onClick={() => setOpen(!open)}
            >
              <X className="w-5 h-5" />
            </div>
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export const SidebarLink = ({
  link,
  className,
  ...props
}: {
  link: Links;
  className?: string;
  [key: string]: any;
}) => {
  const { open, animate } = useSidebar();
  return (
    <button
      onClick={link.onClick}
      title={!open ? link.label : undefined}
      className={cn(
        "flex items-center group/sidebar transition-all duration-150 cursor-pointer text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-neutral-400",
        open
          ? "w-full justify-start gap-3 py-2.5 px-3 rounded-xl"
          : "w-10 h-10 mx-auto justify-center p-0 rounded-xl",
        link.isActive
          ? "bg-white dark:bg-neutral-800 text-neutral-950 dark:text-white font-semibold shadow-2xs border border-neutral-200/90 dark:border-neutral-700"
          : "text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-200/60 dark:hover:bg-neutral-800/60",
        className
      )}
      {...props}
    >
      <div className="shrink-0 flex items-center justify-center">
        {link.icon}
      </div>

      <motion.span
        animate={{
          display: animate ? (open ? "inline-block" : "none") : "inline-block",
          opacity: animate ? (open ? 1 : 0) : 1,
        }}
        className="text-sm group-hover/sidebar:translate-x-0.5 transition duration-150 whitespace-pre inline-block !p-0 !m-0 truncate flex-1"
      >
        {link.label}
      </motion.span>

      {link.badge !== undefined && (
        <motion.span
          animate={{
            display: animate ? (open ? "inline-block" : "none") : "inline-block",
            opacity: animate ? (open ? 1 : 0) : 1,
          }}
          className="ml-auto text-xs px-2 py-0.5 rounded-full font-semibold bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-white shrink-0"
        >
          {link.badge}
        </motion.span>
      )}
    </button>
  );
};
