import { NOT_ADMIN_ERR_MSG, UNAUTHED_ERR_MSG } from '@shared/const';
import { initTRPC, TRPCError } from "@trpc/server";
import superjson from "superjson";
import type { TrpcContext } from "./context";

const t = initTRPC.context<TrpcContext>().create({
  transformer: superjson,
});

export const router = t.router;
export const publicProcedure = t.procedure;

const requireUser = t.middleware(async opts => {
  const { ctx, next } = opts;

  if (!ctx.user) {
    throw new TRPCError({ code: "UNAUTHORIZED", message: UNAUTHED_ERR_MSG });
  }

  return next({
    ctx: {
      ...ctx,
      user: ctx.user,
    },
  });
});

const requirePasswordChangeCompleted = t.middleware(async opts => {
  if (opts.ctx.user?.mustChangePassword) {
    throw new TRPCError({ code: "FORBIDDEN", message: "首次登录后必须先修改初始密码" });
  }
  return opts.next();
});

export const passwordChangeProcedure = t.procedure.use(requireUser);
export const protectedProcedure = t.procedure.use(requireUser).use(requirePasswordChangeCompleted);

export const adminProcedure = t.procedure.use(
  requireUser.unstable_pipe(requirePasswordChangeCompleted).unstable_pipe(t.middleware(async opts => {
    const { ctx, next } = opts;

    if (!ctx.user || ctx.user.role !== 'admin') {
      throw new TRPCError({ code: "FORBIDDEN", message: NOT_ADMIN_ERR_MSG });
    }

    return next({
      ctx: {
        ...ctx,
        user: ctx.user,
      },
    });
  })),
);
