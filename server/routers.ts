import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { passwordChangeProcedure, publicProcedure, router } from "./_core/trpc";
import { opsRouter } from "./routers/ops";

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user ? { ...opts.ctx.user, mustChangePassword: Boolean(opts.ctx.user.mustChangePassword) } : null),
    localPasswordStatus: passwordChangeProcedure.query(({ ctx }) => ({ mustChangePassword: Boolean(ctx.user.mustChangePassword), isLocalAccount: ctx.user.openId.startsWith("local:") })),
    logout: publicProcedure.mutation(({ ctx }) => {
      const cookieOptions = getSessionCookieOptions(ctx.req);
      ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 });
      return { success: true } as const;
    }),
  }),
  ops: opsRouter,
});

export type AppRouter = typeof appRouter;
